"""
AEGIS Intelligence API.

Route layout follows the plane split described in identity.py:

    /guard/*        data plane    — agents submit spend intents
    /policies/*     control plane — operators change what is enforced
    /guardrails/*   control plane — operators arm and disarm guardrails

Reads are open; only mutation is gated. An agent credential is rejected on the
control plane even when that plane is otherwise open, so a compromised agent
can never widen its own authority.
"""

from typing import Optional, Union

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

import anchor
import config
import guard
import seed
from identity import Principal, require_agent, require_operator

from blockchain import (
    get_blockchain_record,
    get_blockchain_records,
    get_blockchain_stats,
    verify_blockchain,
)
from policy_builder import generate_policy_suggestions
from policy_store import apply_policy_suggestion, get_policy_config, toggle_guardrail
from request_history import decide_request, get_dashboard_stats, get_requests
from selector import get_capabilities, select_api

from x402.payment_models import PaymentAuthorization, PaymentRequest
from x402.payment_service import (
    all_payments,
    authorize_payment,
    create_payment_request,
    get_payment,
    settle_payment,
    verify_payment,
)


app = FastAPI(title="AEGIS Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    seed.ensure_demo_data()


# ============================================================================
# MODELS
# ============================================================================

class PromptRequest(BaseModel):
    message: str


class DecisionRequest(BaseModel):
    decision: str


class GuardrailToggleRequest(BaseModel):
    enabled: bool


class SpendIntent(BaseModel):
    """
    What an agent is allowed to ask for.

    Note what is absent: no URL, no payee address, no arbitrary amount. An
    agent names a task, or a provider AEGIS already knows. That is what stops
    an injected "pay quickpay-services.net" instruction from having anywhere
    to enter the system.
    """

    task: str
    provider: Optional[str] = None
    category: Optional[str] = None


class PaymentRequestCreate(BaseModel):
    request_id: str
    task: str
    provider: str
    api: str
    amount: float


class PolicySuggestionPayload(BaseModel):
    """
    An operator-approved policy suggestion.

    Previously this route took a bare `dict`, so a malformed body reached the
    store logic unvalidated. Extra fields are still accepted — the frontend
    round-trips the whole suggestion object, including display-only fields —
    but the two the store actually reads are now typed.
    """

    model_config = ConfigDict(extra="allow")

    suggestion_type: str
    suggested_value: Optional[Union[str, float, int]] = None


# ============================================================================
# META
# ============================================================================

@app.get("/")
def home():
    return {"message": "AEGIS API is running 🚀"}


@app.get("/config")
def get_config():
    """
    The system's real posture, stated plainly.

    The UI reads this so it can show whether the control plane is actually
    locked and whether the ledger is actually anchored, rather than implying
    guarantees that are not configured.
    """

    return config.public_config()


# ============================================================================
# DATA PLANE — the guard
# ============================================================================

@app.post("/guard/spend")
def guard_spend(
    intent: SpendIntent,
    principal: Principal = Depends(require_agent),
):
    """
    The one path money can take.

    AEGIS evaluates the intent and, only if policy allows, performs the paid
    call itself using a credential the agent has never held. Refusals return
    403 with the failed checks attached.
    """

    try:
        result = guard.spend(
            task=intent.task,
            agent_id=principal.name,
            provider=intent.provider,
            category=intent.category,
        )

    except guard.Refusal as refusal:
        raise HTTPException(
            status_code=422,
            detail={"reason": refusal.reason, **refusal.detail},
        )

    if not result["allowed"] and result["status"] == "rejected":
        raise HTTPException(status_code=403, detail=result)

    return result


@app.get("/guard/capabilities")
def guard_capabilities():
    return guard.capabilities()


# ============================================================================
# TASK SUBMISSION (legacy entry point, same engine)
# ============================================================================

@app.post("/execute-task")
def execute_task(request: PromptRequest):
    return select_api(request.message)


@app.get("/capabilities")
def capabilities():
    return get_capabilities()


# ============================================================================
# REQUESTS
# ============================================================================

@app.get("/requests")
def requests():
    return get_requests()


@app.post("/requests/{request_id}/decision")
def make_decision(request_id: str, body: DecisionRequest):
    """
    Apply a human decision to a request awaiting review.

    Idempotent: re-approving an already-approved request returns the existing
    record instead of creating a second payment and a second transaction ID.
    """

    decision = body.decision.lower().strip()

    if decision not in {"approved", "rejected"}:
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'approved' or 'rejected'.",
        )

    updated = decide_request(request_id, decision)

    if updated is None:
        raise HTTPException(status_code=404, detail="Payment request not found.")

    if updated.get("alreadyDecided"):
        return {
            **updated,
            "payment_created": False,
            "message": f"Request was already {updated['status']}; no action taken.",
        }

    if decision != "approved":
        return {
            **updated,
            "payment_created": False,
            "payment_id": None,
            "transaction_id": None,
            "payment_status": None,
        }

    try:
        payment = create_payment_request(
            request_id=request_id,
            task=updated.get("task", "Approved payment request"),
            provider=updated.get("provider", "Unknown Provider"),
            api=updated.get("api", "x402 Payment API"),
            amount=float(updated.get("amount", 0)),
        )

    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Payment creation failed: {exc}",
        ) from exc

    return {
        **updated,
        "payment_created": True,
        "payment_id": payment["payment_id"],
        "transaction_id": payment["transaction_id"],
        "payment_status": payment["status"],
        "payment": payment,
    }


@app.get("/dashboard")
def dashboard():
    return get_dashboard_stats()


# ============================================================================
# LEDGER
# ============================================================================

@app.get("/blockchain")
def blockchain():
    return get_blockchain_records()


@app.get("/blockchain/stats")
def blockchain_stats():
    return get_blockchain_stats()


@app.get("/blockchain/verify")
def blockchain_verify():
    return verify_blockchain()


@app.get("/blockchain/anchors")
def blockchain_anchors():
    return {"status": anchor.status(), "anchors": anchor.get_anchors()}


@app.get("/blockchain/anchors/preflight")
def blockchain_anchor_preflight():
    """
    Check anchoring is usable without spending anything.

    Reads the key, derives the address, and queries balance, gas price and
    nonce. Never broadcasts. Run before a demo rather than discovering at
    block 5 that the account is unfunded.
    """

    return anchor.preflight()


@app.get("/blockchain/{block_number}")
def blockchain_block(block_number: int):
    block = get_blockchain_record(block_number)

    # Previously returned {"error": ...} with HTTP 200, which is invisible to
    # any client checking response.ok.
    if block is None:
        raise HTTPException(status_code=404, detail="Block not found.")

    return block


# ============================================================================
# CONTROL PLANE — policy
# ============================================================================

@app.get("/policies")
def policies():
    return get_policy_config()


@app.get("/policy-suggestions")
def policy_suggestions():
    return generate_policy_suggestions()


@app.post("/policies/apply")
def apply_policy(
    suggestion: PolicySuggestionPayload,
    principal: Principal = Depends(require_operator),
):
    """
    Apply an operator-approved policy suggestion. Control plane only.
    """

    try:
        return apply_policy_suggestion(suggestion.model_dump())

    except ValueError as exc:
        return {"success": False, "message": str(exc)}


# ============================================================================
# CONTROL PLANE — guardrails
# ============================================================================

GUARDRAIL_DEFINITIONS = {
    "provider_allow_list": {
        "name": "Provider Allow List",
        "category": "access",
        "description": "Controls which providers agents may use.",
        "threshold": lambda cfg: f"{len(cfg['allowed_providers'])} providers allowed",
    },
    "auto_approval_limit": {
        "name": "Autonomous Approval Limit",
        "category": "spending",
        "description": "Maximum amount that can be automatically approved.",
        "threshold": lambda cfg: f"${cfg['auto_approve_limit']:,.0f}",
    },
    "human_review_limit": {
        "name": "Human Review Threshold",
        "category": "compliance",
        "description": "Transactions above the autonomous limit require human approval.",
        "threshold": lambda cfg: f"Up to ${cfg['human_review_limit']:,.0f}",
    },
    "daily_budget": {
        "name": "Daily Spending Budget",
        "category": "spending",
        "description": "Maximum allowed spending per day.",
        "threshold": lambda cfg: f"${cfg['daily_budget']:,.0f}",
    },
    "frequency_limit": {
        "name": "Request Frequency Limit",
        "category": "behavioral",
        "description": "Limits how many requests can be processed within the window.",
        "threshold": lambda cfg: (
            f"{cfg['frequency_limit']} requests / "
            f"{cfg.get('frequency_window_hours', 24)}h"
        ),
    },
}


def _describe_guardrail(guardrail_id: str, cfg: dict) -> dict:
    definition = GUARDRAIL_DEFINITIONS[guardrail_id]

    return {
        "id": guardrail_id,
        "name": definition["name"],
        "category": definition["category"],
        "description": definition["description"],
        "threshold": definition["threshold"](cfg),
        "enabled": cfg["guardrails_enabled"][guardrail_id],
        "triggeredCount": 0,
    }


@app.get("/guardrails")
def guardrails():
    cfg = get_policy_config()

    return [_describe_guardrail(key, cfg) for key in GUARDRAIL_DEFINITIONS]


@app.post("/guardrails/{guardrail_id}/toggle")
def guardrail_toggle(
    guardrail_id: str,
    body: GuardrailToggleRequest,
    principal: Principal = Depends(require_operator),
):
    """
    Arm or disarm a guardrail. Control plane only.

    This is the route a prompt-injected agent would most like to reach. It
    cannot: an agent credential is rejected here by construction, and with
    AEGIS_OPERATOR_TOKEN set the route is closed to anonymous callers too.
    """

    if guardrail_id not in GUARDRAIL_DEFINITIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown guardrail: {guardrail_id}",
        )

    try:
        cfg = toggle_guardrail(guardrail_id, body.enabled)

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _describe_guardrail(guardrail_id, cfg)


# ============================================================================
# x402 PAYMENT LIFECYCLE
# ============================================================================

@app.post("/x402/payment")
def create_x402_payment(request: PaymentRequest):
    try:
        payment = create_payment_request(
            request_id=request.request_id,
            task=request.task,
            provider=request.provider,
            api=request.api,
            amount=request.amount,
        )

    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Payment creation failed: {exc}",
        ) from exc

    return {"status": 402, "message": "Payment Required", "payment": payment}


@app.get("/x402/payment/{payment_id}")
def read_x402_payment(payment_id: str):
    payment = get_payment(payment_id)

    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment


@app.post("/x402/payment/{payment_id}/authorize")
def authorize_x402_payment(payment_id: str, body: PaymentAuthorization):
    payment = authorize_payment(payment_id, body.payment_signature)

    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment


@app.post("/x402/payment/{payment_id}/verify")
def verify_x402_payment(payment_id: str):
    payment = verify_payment(payment_id)

    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment


@app.post("/x402/payment/{payment_id}/settle")
def settle_x402_payment(payment_id: str):
    payment = settle_payment(payment_id)

    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment


@app.post("/x402/execute/{payment_id}")
def execute_x402_payment(payment_id: str):
    payment = get_payment(payment_id)

    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment["status"] != "settled":
        raise HTTPException(status_code=400, detail="Payment has not been settled.")

    return {
        "success": True,
        "payment_id": payment_id,
        "transaction_hash": payment["transaction_hash"],
        "settlement_mode": payment.get("settlement_mode", "simulated"),
        "provider": payment["provider"],
        "api": payment["api"],
        "task": payment["task"],
        "message": "Payment settled. Service execution authorized.",
    }


# ============================================================================
# PAYMENTS & TRANSACTIONS
# ============================================================================

@app.post("/payments/request")
def create_payment(data: PaymentRequestCreate):
    try:
        payment = create_payment_request(
            request_id=data.request_id,
            task=data.task,
            provider=data.provider,
            api=data.api,
            amount=data.amount,
        )

    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"Payment creation failed: {exc}",
        ) from exc

    return {"success": True, **payment}


@app.get("/transactions")
def transactions():
    return [
        {
            "id": payment.get("transaction_id"),
            "request_id": payment.get("request_id"),
            "payment_id": payment.get("payment_id"),
            "task": payment.get("task"),
            "provider": payment.get("provider"),
            "api": payment.get("api"),
            "amount": payment.get("amount"),
            "currency": payment.get("currency", "USDC"),
            "network": payment.get("network", "Base Sepolia"),
            "pay_to": payment.get("pay_to"),
            "status": payment.get("status", "payment_required"),
            "settlement_mode": payment.get("settlement_mode", "simulated"),
            "transaction_hash": payment.get("transaction_hash"),
            "payment_signature": payment.get("payment_signature"),
            "created_at": payment.get("created_at"),
            "settled_at": payment.get("settled_at"),
        }
        for payment in all_payments()
    ]


@app.get("/payments/{payment_id}")
def payment_details(payment_id: str):
    payment = get_payment(payment_id)

    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {"success": True, "payment": payment}
