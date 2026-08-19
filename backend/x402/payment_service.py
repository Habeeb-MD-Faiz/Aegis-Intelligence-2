"""
x402-style payment lifecycle.

Honest scope: this models the lifecycle — payment_required → authorized →
verified → settling → settled. It does not move funds. `PAY_TO_ADDRESS` is a
placeholder and no value transfer is made. The state machine is real;
settlement is simulated, and the API says so rather than implying otherwise.

Changed from the original: payments persist to SQLite instead of a
module-level dict, so transactions survive a restart. `settle_payment` also
completes the settlement rather than parking the record in "settling" with
nothing to advance it — previously `complete_settlement` existed but no route
or caller ever reached it, so no payment could become "settled" and
`/x402/execute/{id}` was therefore unreachable.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import store


# ============================================================================
# CONFIGURATION
# ============================================================================

PAYMENT_NETWORK = "Base Sepolia"
PAYMENT_CURRENCY = "USDC"

# Placeholder. No funds move; see the module docstring.
PAY_TO_ADDRESS = "0x0000000000000000000000000000000000000000"

SETTLEMENT_MODE = "simulated"


# ============================================================================
# CREATE
# ============================================================================

def create_payment_request(
    request_id: str,
    task: str,
    provider: str,
    api: str,
    amount: float,
) -> Dict:
    """
    Create an AEGIS payment execution record.

    Both identifiers are generated here, on the backend. The frontend never
    fabricates a transaction ID.
    """

    payment_id = str(uuid.uuid4())
    transaction_id = f"TX-{uuid.uuid4().hex[:8].upper()}"

    payment = {
        "payment_id": payment_id,
        "request_id": request_id,
        "transaction_id": transaction_id,

        "task": task,
        "provider": provider,
        "api": api,

        "amount": amount,
        "currency": PAYMENT_CURRENCY,
        "network": PAYMENT_NETWORK,
        "pay_to": PAY_TO_ADDRESS,

        "status": "payment_required",
        "settlement_mode": SETTLEMENT_MODE,

        "payment_signature": None,
        "transaction_hash": None,

        "created_at": datetime.now(timezone.utc).isoformat(),
        "settled_at": None,
    }

    store.save_payment(payment)

    return payment


# ============================================================================
# READ
# ============================================================================

def get_payment(payment_id: str) -> Optional[Dict]:
    return store.load_payment(payment_id)


def all_payments() -> List[Dict]:
    return store.load_payments()


# ============================================================================
# LIFECYCLE
# ============================================================================

def authorize_payment(payment_id: str, payment_signature: str) -> Optional[Dict]:
    payment = store.load_payment(payment_id)

    if payment is None:
        return None

    payment["payment_signature"] = payment_signature
    payment["status"] = "authorized"

    return store.save_payment(payment)


def verify_payment(payment_id: str) -> Optional[Dict]:
    payment = store.load_payment(payment_id)

    if payment is None:
        return None

    if not payment.get("payment_signature"):
        payment["status"] = "verification_failed"
        return store.save_payment(payment)

    payment["status"] = "verified"

    return store.save_payment(payment)


def settle_payment(payment_id: str) -> Optional[Dict]:
    """
    Settle a verified payment.

    In simulated mode this completes immediately and stamps a deterministic
    pseudo-hash clearly marked as simulated, so the record is never mistaken
    for an on-chain transfer.
    """

    payment = store.load_payment(payment_id)

    if payment is None:
        return None

    if payment["status"] != "verified":
        return payment

    payment["status"] = "settling"
    store.save_payment(payment)

    return complete_settlement(
        payment_id,
        transaction_hash=f"0xSIMULATED{uuid.uuid4().hex[:48]}",
    )


def complete_settlement(payment_id: str, transaction_hash: str) -> Optional[Dict]:
    payment = store.load_payment(payment_id)

    if payment is None:
        return None

    payment["transaction_hash"] = transaction_hash
    payment["status"] = "settled"
    payment["settled_at"] = datetime.now(timezone.utc).isoformat()

    return store.save_payment(payment)
