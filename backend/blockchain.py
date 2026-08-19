import hashlib
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from typing import Dict, List

import anchor
import config


# ============================================================
# Configuration
# ============================================================

BLOCKCHAIN_FILE = config.LEDGER_FILE


# ============================================================
# Concurrency
# ============================================================
#
# Appending a block is a read-modify-write over the whole file. Two concurrent
# requests could previously both load the same chain, both append at the same
# block number, and the second write would silently discard the first — losing
# an audit record and breaking the hash linkage.
#
# The whole sequence now runs under one lock, and writes are atomic: we write a
# temporary file in the same directory and os.replace() it, which is atomic on
# POSIX and Windows. A crash mid-write can no longer truncate the ledger.

_chain_lock = threading.RLock()


# ============================================================
# Storage
# ============================================================

def _load_chain() -> List[Dict]:
    """
    Load the blockchain from disk.

    If the file doesn't exist yet, start with an empty chain.
    """

    if not BLOCKCHAIN_FILE.exists():
        return []

    try:
        with open(BLOCKCHAIN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        return data

    except (json.JSONDecodeError, OSError):
        return []


def _save_chain(chain: List[Dict]) -> None:
    """
    Persist the entire chain to disk atomically.
    """

    BLOCKCHAIN_FILE.parent.mkdir(parents=True, exist_ok=True)

    handle, temporary_path = tempfile.mkstemp(
        dir=str(BLOCKCHAIN_FILE.parent),
        prefix=".ledger-",
        suffix=".tmp",
    )

    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            json.dump(chain, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temporary_path, BLOCKCHAIN_FILE)

    except BaseException:
        # Never leave a stray temp file behind on failure.
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise


# ============================================================
# Hashing
# ============================================================

def _calculate_hash(block_data: Dict) -> str:
    """
    Create a deterministic SHA-256 hash for a block.
    """

    block_string = json.dumps(
        block_data,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        block_string.encode("utf-8")
    ).hexdigest()


# ============================================================
# Block creation
# ============================================================

def create_blockchain_record(request: Dict) -> Dict:
    """
    Create and permanently store a blockchain audit record
    for a finalized payment request.

    This function should ONLY be called after a final decision.

    The load-append-save sequence holds a lock for its whole duration, so two
    concurrent decisions cannot claim the same block number or overwrite each
    other's record.
    """

    with _chain_lock:
        return _append_block(request)


def _append_block(request: Dict) -> Dict:
    chain = _load_chain()

    # Prevent duplicate records for the same request.
    existing = next(
        (
            block
            for block in chain
            if block.get("requestId") == request.get("id")
        ),
        None
    )

    if existing:
        return existing

    timestamp = datetime.now(timezone.utc).isoformat()

    if chain:
        previous_hash = chain[-1]["hash"]
    else:
        previous_hash = "GENESIS"

    block_number = len(chain) + 1

    block_data = {
        "blockNumber": block_number,
        "requestId": request["id"],
        "task": request["task"],
        "provider": request["provider"],
        "amount": request["amount"],
        "category": request.get("category"),
        "decision": request["status"],
        "decisionType": request.get("decision"),
        "decisionBy": request.get("decisionBy"),
        "reason": request.get("reason"),
        "timestamp": timestamp,
        "previousHash": previous_hash,
    }

    hash_payload = {
        "blockNumber": block_data["blockNumber"],
        "requestId": block_data["requestId"],
        "task": block_data["task"],
        "provider": block_data["provider"],
        "amount": block_data["amount"],
        "category": block_data["category"],
        "decision": block_data["decision"],
        "decisionType": block_data["decisionType"],
        "decisionBy": block_data["decisionBy"],
        "reason": block_data["reason"],
        "timestamp": block_data["timestamp"],
        "previousHash": block_data["previousHash"],
    }

    block_hash = _calculate_hash(hash_payload)

    block = {
        **block_data,
        "hash": block_hash,
    }

    chain.append(block)

    _save_chain(chain)

    # Periodically commit the chain head to Base Sepolia so local history
    # cannot be rewritten without also altering a record we do not control.
    # Best-effort: a slow testnet must never block a payment decision.
    if config.ANCHORING_ENABLED and block_number % config.ANCHOR_EVERY == 0:
        anchor.anchor_head(block_number, block_hash)

    return block


# ============================================================
# Read blockchain
# ============================================================

def get_blockchain_records() -> List[Dict]:
    """
    Return every blockchain block.
    """

    return _load_chain()


# ============================================================
# Get a single block
# ============================================================

def get_blockchain_record(block_number: int) -> Dict | None:
    """
    Return one block by block number.
    """

    chain = _load_chain()

    for block in chain:
        if block["blockNumber"] == block_number:
            return block

    return None


# ============================================================
# Verify blockchain integrity
# ============================================================

def verify_blockchain() -> Dict:
    """
    Verify:

    1. Block numbering
    2. Previous hash relationships
    3. Current block hashes
    """

    chain = _load_chain()

    if not chain:
        return {
            "valid": True,
            "message": "Blockchain is empty.",
            "blocks": 0,
            "verifiedBlocks": 0,
            "tamperedBlocks": 0,
        }

    for index, block in enumerate(chain):

        # ----------------------------------------------------
        # Verify block number
        # ----------------------------------------------------

        expected_block_number = index + 1

        if block.get("blockNumber") != expected_block_number:
            return {
                "valid": False,
                "message": (
                    f"Block number mismatch at block "
                    f"{block.get('blockNumber')}"
                ),
                "blocks": len(chain),
                "verifiedBlocks": index,
                "tamperedBlocks": 1,
            }

        # ----------------------------------------------------
        # Verify previous hash
        # ----------------------------------------------------

        if index == 0:
            expected_previous_hash = "GENESIS"
        else:
            expected_previous_hash = chain[index - 1]["hash"]

        if block.get("previousHash") != expected_previous_hash:
            return {
                "valid": False,
                "message": (
                    f"Previous hash mismatch at block "
                    f"{block['blockNumber']}"
                ),
                "blocks": len(chain),
                "verifiedBlocks": index,
                "tamperedBlocks": 1,
                "tamperedBlock": block["blockNumber"],
            }

        # ----------------------------------------------------
        # Reconstruct block payload
        # ----------------------------------------------------

        hash_payload = {
            "blockNumber": block["blockNumber"],
            "requestId": block["requestId"],
            "task": block["task"],
            "provider": block["provider"],
            "amount": block["amount"],
            "category": block.get("category"),
            "decision": block["decision"],
            "decisionType": block.get("decisionType"),
            "decisionBy": block.get("decisionBy"),
            "reason": block.get("reason"),
            "timestamp": block["timestamp"],
            "previousHash": block["previousHash"],
        }

        expected_hash = _calculate_hash(hash_payload)

        # ----------------------------------------------------
        # Verify current hash
        # ----------------------------------------------------

        if block.get("hash") != expected_hash:
            return {
                "valid": False,
                "message": (
                    f"Hash mismatch at block "
                    f"{block['blockNumber']}"
                ),
                "blocks": len(chain),
                "verifiedBlocks": index,
                "tamperedBlocks": 1,
                "tamperedBlock": block["blockNumber"],
            }

    return {
        "valid": True,
        "message": "Blockchain integrity verified.",
        "blocks": len(chain),
        "verifiedBlocks": len(chain),
        "tamperedBlocks": 0,
    }


# ============================================================
# Blockchain statistics
# ============================================================

def get_blockchain_stats() -> Dict:
    """
    Return statistics used by the blockchain dashboard.
    """

    chain = _load_chain()

    verification = verify_blockchain()

    return {
        "totalBlocks": len(chain),
        "chainStatus": (
            "verified"
            if verification["valid"]
            else "compromised"
        ),
        "verifiedBlocks": verification["verifiedBlocks"],
        "tamperedBlocks": verification["tamperedBlocks"],
        "latestBlock": chain[-1] if chain else None,

        # Reported so the UI can state the ledger's real security posture
        # rather than implying a distributed chain that does not exist.
        "anchoring": anchor.status(),
    }