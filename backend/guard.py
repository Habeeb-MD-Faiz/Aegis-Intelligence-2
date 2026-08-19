"""
The guard — AEGIS's policy enforcement point.

Everything else in AEGIS decides. This module is the thing that *stops*.

The distinction matters more than it sounds. The original architecture was a
policy decision point: an agent asked AEGIS whether a payment was acceptable,
and AEGIS answered. An agent that never asked was unaffected, which makes the
control advisory rather than enforceable.

Here the flow is inverted. The agent cannot pay anyone, because it holds no
credential (see credentials.py). It submits an intent; AEGIS evaluates it and,
only if policy allows, performs the call itself. Refusing is the default and
requires no cooperation from the agent.

Three structural properties do the work:

  1. Credential custody   — the agent has nothing to pay with.
  2. Catalog-bound payees — an agent names a known provider, never a URL or an
                            address, so injected payment instructions have no
                            way into the system.
  3. Fail closed          — if policy evaluation errors, the answer is no.
"""

from datetime import datetime, timezone
from typing import Optional

import catalog
import config
import credentials
import risk
from blockchain import create_blockchain_record
from guardrails import evaluate_payment
from request_history import add_request
from x402.payment_service import create_payment_request


# ============================================================
# OUTCOMES
# ============================================================

APPROVED = "approved"
HUMAN_REVIEW = "human_review"
BLOCKED = "blocked"


class Refusal(Exception):
    """
    The guard declined before policy evaluation — an unresolvable or
    unauthorized intent. Carries the reason so the agent (and the audit trail)
    learn why.
    """

    def __init__(self, reason: str, detail: Optional[dict] = None):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail or {}


# ============================================================
# INTENT RESOLUTION
# ============================================================

def resolve_intent(
    task: str,
    provider: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    """
    Turn an agent's intent into a concrete, known service.

    This is the choke point for injected payment instructions. An agent may
    name a provider that exists in our catalog, or describe a task we can map
    to a category. Anything else is refused here, before policy ever runs —
    a payee we have never heard of is not a policy question, it is a
    malformed request.
    """

    if provider:
        entry = catalog.find_provider(provider, category)

        if entry is None:
            raise Refusal(
                f"'{provider}' is not a known provider. "
                "AEGIS only pays services in its catalog.",
                {
                    "requestedProvider": provider,
                    "knownProviders": catalog.KNOWN_PROVIDERS,
                },
            )

        return entry

    match = catalog.select_category(task)

    if match is None:
        raise Refusal(
            "No catalog service matches this task.",
            {
                "task": task,
                "capabilities": catalog.describe_capabilities(),
            },
        )

    selected = catalog.cheapest_in_category(match["category"])

    if selected is None:
        raise Refusal(
            f"Category '{match['category']}' has no available services.",
            {"category": match["category"]},
        )

    return {
        **selected,
        "category": match["category"],
        "matchedOn": match["matchedOn"],
    }


# ============================================================
# POLICY EVALUATION
# ============================================================

def evaluate(provider: str, amount: float) -> dict:
    """
    Run the policy engine, failing closed.

    A guard that allows payments when its own evaluation crashes is not a
    guard. Set AEGIS_GUARD_FAIL_OPEN=true only if you understand what you are
    trading away.
    """

    try:
        return evaluate_payment(provider, amount)

    except Exception as exc:  # noqa: BLE001 - deliberate catch-all
        if config.GUARD_FAIL_OPEN:
            return {
                "decision": APPROVED,
                "reason": f"Policy engine unavailable; failing open: {exc}",
                "riskLevel": "high",
                "checks": [
                    {
                        "policy": "Policy Engine",
                        "passed": False,
                        "message": f"Evaluation error, failed open: {exc}",
                    }
                ],
            }

        return {
            "decision": BLOCKED,
            "reason": "Policy engine unavailable; refusing by default.",
            "riskLevel": "high",
            "checks": [
                {
                    "policy": "Policy Engine",
                    "passed": False,
                    "message": f"Evaluation error, failed closed: {exc}",
                }
            ],
        }


# ============================================================
# OUTBOUND EXECUTION
# ============================================================

def _execute_outbound(service: dict, task: str) -> dict:
    """
    Perform the paid call on the agent's behalf.

    The credential is read here and nowhere else, and never leaves this
    function — not into the response, not into the ledger, not into a log.

    Catalog entries without an `endpoint` are fulfilled in simulation. That is
    reported honestly as fulfilment: "simulated" rather than dressed up as a
    live call, because claiming otherwise is exactly the kind of thing that
    falls apart under questioning.
    """

    provider = service["provider"]
    endpoint = catalog.resolve_endpoint(provider, service)

    if not endpoint:
        return {
            "fulfilment": "simulated",
            "note": (
                "No live endpoint configured for this provider. "
                "Authorization and credential injection are real; "
                "the upstream call is simulated."
            ),
            "credentialHeld": credentials.has_credential(provider),
        }

    secret = credentials.get_credential(provider)

    if secret is None:
        return {
            "fulfilment": "unavailable",
            "note": (
                f"No credential held for {provider}. "
                "AEGIS will not forward an unauthenticated call."
            ),
            "credentialHeld": False,
        }

    try:
        import requests  # imported lazily; only needed for live providers

        response = requests.post(
            endpoint,
            json={"task": task},
            headers={"Authorization": f"Bearer {secret}"},
            timeout=config.GUARD_REQUEST_TIMEOUT,
        )

        return {
            "fulfilment": "live",
            "status": response.status_code,
            "body": credentials.redact(response.text[:2000]),
            "credentialHeld": True,
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "fulfilment": "failed",
            "note": credentials.redact(str(exc)),
            "credentialHeld": True,
        }


# ============================================================
# THE GUARD
# ============================================================

def spend(
    task: str,
    agent_id: str = "unidentified-agent",
    provider: Optional[str] = None,
    category: Optional[str] = None,
) -> dict:
    """
    The one path money can take.

    Returns a decision envelope in every case — approved, escalated or
    refused. Refusals are first-class results with reasons attached, not
    exceptions to be swallowed by a caller.
    """

    service = resolve_intent(task, provider, category)

    amount = float(service.get("cost", 0))
    provider_name = service["provider"]

    verdict = evaluate(provider_name, amount)
    decision = verdict["decision"]

    # Behavioural risk is assessed independently of the policy decision, then
    # reconciled: risk can raise the level but never lower it below what the
    # decision implies. Computed before the record is stored so the agent's
    # own history does not include the request being scored.
    assessment = risk.assess(
        agent_id=agent_id,
        provider=provider_name,
        amount=amount,
        category=service.get("category"),
    )

    status = {
        APPROVED: "approved",
        HUMAN_REVIEW: "pending",
        BLOCKED: "rejected",
    }.get(decision, "rejected")

    record = {
        "task": task,
        "provider": provider_name,
        "api": service["name"],
        "amount": amount,
        "category": service.get("category"),
        "agentId": agent_id,
        "decision": decision,
        "riskLevel": risk.combine(decision, assessment),
        "riskScore": assessment["score"],
        "riskSignals": assessment["signals"],
        "riskSummary": assessment["summary"],
        "reason": verdict["reason"],
        "checks": verdict["checks"],
        "status": status,
        "decisionBy": "Guardrails",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }

    saved = add_request(record)

    # Final decisions are written to the ledger immediately. Escalations wait
    # for the human, so the ledger records what was actually decided rather
    # than what was proposed.
    if decision in (APPROVED, BLOCKED):
        create_blockchain_record(saved)

    envelope = {
        **saved,
        "allowed": decision == APPROVED,
        "alternatives": [
            {"provider": item["provider"], "name": item["name"], "cost": item["cost"]}
            for item in catalog.alternatives(service.get("category", ""))
        ],
    }

    if decision == APPROVED:
        payment = create_payment_request(
            request_id=saved["id"],
            task=task,
            provider=provider_name,
            api=service["name"],
            amount=amount,
        )

        envelope["payment"] = payment
        envelope["paymentId"] = payment["payment_id"]
        envelope["transactionId"] = payment["transaction_id"]
        envelope["execution"] = _execute_outbound(service, task)

    return envelope


def capabilities() -> dict:
    """
    What the guard is willing to pay for, and what it holds credentials for.
    """

    return {
        "providers": catalog.KNOWN_PROVIDERS,
        "categories": catalog.describe_capabilities(),
        "credentialsHeld": credentials.describe(),
    }
