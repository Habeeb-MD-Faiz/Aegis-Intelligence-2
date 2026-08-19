"""
Ledger anchoring on Base Sepolia.

Why this exists:

The local ledger is a SHA-256 hash chain in a file written by the same process
that serves the API. That makes it tamper-*evident* only against an attacker
who does not also recompute the chain — which is anyone with write access to
the file. Calling that a blockchain invites exactly one question, and there is
no good answer to it.

Anchoring fixes the claim rather than the wording. Periodically we write the
current chain head to Base Sepolia. Rewriting local history now also requires
altering a record we do not control.

Deliberately *not* implemented: moving real funds. The problem we are solving
is the guard, not the rail, and a live value transfer is one more thing that
can fail in front of an audience. This writes a hash, nothing else.

Structure note: transaction *building and signing* is separated from
*broadcasting* so the risky, fiddly part can be tested offline with a
throwaway key and no network — see test_anchor.py. Only the final
eth_sendRawTransaction needs a funded account.

Anchoring is optional. With no key configured it is skipped and reported as
disabled — we never claim an anchor we did not write.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

import config


BASE_SEPOLIA_CHAIN_ID = 84532

# Intrinsic cost of a transaction, plus per-byte calldata cost. Non-zero
# calldata bytes cost 16 gas, zero bytes 4; we assume the expensive case and
# add headroom so an anchor cannot fail for being a few gas short.
BASE_GAS = 21_000
GAS_PER_CALLDATA_BYTE = 16
GAS_HEADROOM = 10_000

# Anchors written this process lifetime, newest last.
_anchors: List[Dict] = []


# ============================================================
# RPC
# ============================================================

def rpc(method: str, params: list) -> str:
    """
    One JSON-RPC call against the configured endpoint.
    """

    import requests

    response = requests.post(
        config.CHAIN_RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=config.GUARD_REQUEST_TIMEOUT,
    )

    response.raise_for_status()
    payload = response.json()

    if "error" in payload:
        raise RuntimeError(payload["error"].get("message", "RPC error"))

    return payload["result"]


# ============================================================
# PAYLOAD
# ============================================================

def build_payload(block_number: int, chain_head: str) -> bytes:
    """
    The calldata carried on-chain: a tagged chain head, so an observer can tell
    what the anchor refers to without access to our database.
    """

    return json.dumps(
        {"aegis": "ledger-anchor", "block": block_number, "head": chain_head},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def decode_payload(data: str) -> Optional[Dict]:
    """
    Read an anchor back out of a transaction's calldata. Used by tests and by
    anyone verifying an anchor from a block explorer.
    """

    try:
        raw = bytes.fromhex(data[2:] if data.startswith("0x") else data)
        parsed = json.loads(raw.decode("utf-8"))

    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    return parsed if parsed.get("aegis") == "ledger-anchor" else None


def estimate_gas(payload: bytes) -> int:
    return BASE_GAS + GAS_PER_CALLDATA_BYTE * len(payload) + GAS_HEADROOM


# ============================================================
# BUILD + SIGN  (no network)
# ============================================================

def build_transaction(
    address: str,
    nonce: int,
    gas_price: int,
    block_number: int,
    chain_head: str,
) -> Dict:
    """
    A zero-value self-transaction whose calldata carries the chain head.

    Pure function: no network, no key. Testable in isolation.
    """

    payload = build_payload(block_number, chain_head)

    return {
        "nonce": nonce,
        "to": address,
        "value": 0,
        "gas": estimate_gas(payload),
        "gasPrice": gas_price,
        "data": "0x" + payload.hex(),
        "chainId": BASE_SEPOLIA_CHAIN_ID,
    }


def sign_transaction(transaction: Dict, private_key: str) -> str:
    """
    Sign and return the raw hex ready for eth_sendRawTransaction.

    Handles the eth-account rename: `rawTransaction` before 0.13,
    `raw_transaction` after. Getting this wrong is a silent AttributeError at
    the exact moment you want the anchor to work, so both are supported.
    """

    from eth_account import Account

    signed = Account.sign_transaction(transaction, private_key)

    raw = getattr(signed, "raw_transaction", None)

    if raw is None:
        raw = getattr(signed, "rawTransaction", None)

    if raw is None:
        raise RuntimeError(
            "Could not read the raw transaction from eth-account; "
            "unexpected version."
        )

    return "0x" + bytes(raw).hex()


# ============================================================
# STATUS
# ============================================================

def status() -> Dict:
    """
    Honest description of the anchoring subsystem.
    """

    return {
        "enabled": config.ANCHORING_ENABLED,
        "chain": config.CHAIN_NAME,
        "chainId": BASE_SEPOLIA_CHAIN_ID,
        "anchorEvery": config.ANCHOR_EVERY,
        "anchorsWritten": len(_anchors),
        "latestAnchor": _anchors[-1] if _anchors else None,
        "note": (
            f"Chain head is written to {config.CHAIN_NAME} every "
            f"{config.ANCHOR_EVERY} blocks."
            if config.ANCHORING_ENABLED
            else "Anchoring disabled: no AEGIS_CHAIN_PRIVATE_KEY configured. "
            "The ledger is hash-linked and tamper-evident locally, but not "
            "anchored on-chain."
        ),
    }


def get_anchors() -> List[Dict]:
    return list(_anchors)


def reset() -> None:
    _anchors.clear()


# ============================================================
# ANCHOR
# ============================================================

def anchor_head(block_number: int, chain_head: str) -> Optional[Dict]:
    """
    Write a chain head to Base Sepolia.

    Returns the anchor record, or None when anchoring is disabled or fails.
    Failure is never fatal: a guard that stops working because a testnet RPC
    is slow would be a poor trade.
    """

    if not config.ANCHORING_ENABLED:
        return None

    try:
        from eth_account import Account

        account = Account.from_key(config.CHAIN_PRIVATE_KEY)

        nonce = int(rpc("eth_getTransactionCount", [account.address, "pending"]), 16)
        gas_price = int(rpc("eth_gasPrice", []), 16)

        transaction = build_transaction(
            address=account.address,
            nonce=nonce,
            gas_price=gas_price,
            block_number=block_number,
            chain_head=chain_head,
        )

        raw = sign_transaction(transaction, config.CHAIN_PRIVATE_KEY)
        tx_hash = rpc("eth_sendRawTransaction", [raw])

        record = {
            "blockNumber": block_number,
            "chainHead": chain_head,
            "txHash": tx_hash,
            "from": account.address,
            "chain": config.CHAIN_NAME,
            "explorerUrl": f"{config.CHAIN_EXPLORER}{tx_hash}",
            "anchoredAt": datetime.now(timezone.utc).isoformat(),
        }

        _anchors.append(record)

        print(f"⚓ LEDGER ANCHORED: block {block_number} -> {tx_hash}")

        return record

    except Exception as exc:  # noqa: BLE001
        # Anchoring is best-effort. Never let it take the guard down.
        print(f"⚠️  ANCHOR FAILED (non-fatal): {exc!r}")
        return None


def preflight() -> Dict:
    """
    Check anchoring is actually usable, without spending anything.

    Reads the key, derives the address, queries nonce, gas price and balance.
    Run this before a demo instead of discovering at block 5 that the account
    is unfunded.
    """

    if not config.ANCHORING_ENABLED:
        return {"ready": False, "reason": "No AEGIS_CHAIN_PRIVATE_KEY configured."}

    try:
        from eth_account import Account

        account = Account.from_key(config.CHAIN_PRIVATE_KEY)
        balance = int(rpc("eth_getBalance", [account.address, "latest"]), 16)
        gas_price = int(rpc("eth_gasPrice", []), 16)
        nonce = int(rpc("eth_getTransactionCount", [account.address, "pending"]), 16)

        estimated = estimate_gas(build_payload(1, "0" * 64)) * gas_price
        funded = balance >= estimated

        return {
            "ready": funded,
            "address": account.address,
            "chain": config.CHAIN_NAME,
            "balanceWei": balance,
            "estimatedCostWei": estimated,
            "nonce": nonce,
            "reason": (
                "Ready to anchor."
                if funded
                else f"Account {account.address} has insufficient balance. "
                "Fund it from a Base Sepolia faucet."
            ),
        }

    except Exception as exc:  # noqa: BLE001
        return {"ready": False, "reason": f"Preflight failed: {exc}"}
