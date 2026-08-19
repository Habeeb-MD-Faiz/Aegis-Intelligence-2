"""
The policy engine.

Three defects were fixed here, all of which made guardrails look like they
worked while doing nothing:

1. `evaluate_payment` was defined twice in this file. The second definition
   silently shadowed the first, and the dead one was missing the frequency
   check entirely. There is now one.

2. `today_spend` was the hardcoded constant 650, so the daily budget guardrail
   never saw real spending. It is now derived from actual approved requests.

3. The frequency check incremented a module-level counter that nothing ever
   reset, so the third request in any process lifetime was blocked forever.
   Worse, the increment happened *during evaluation*, so requests that were
   later blocked on provider or budget still consumed quota. Frequency is now
   derived from request timestamps in a rolling window — no counter, no reset,
   and evaluation has no side effects.

Evaluation is deliberately deterministic. An LLM proposes policy (see
policy_builder.py); it never decides whether to release money.
"""

from typing import Dict, List, Tuple

from policy_store import get_policy_config
from request_history import requests_in_window, spend_today


# ============================================================
# RESPONSE BUILDER
# ============================================================

RISK_MAP = {
    "approved": "low",
    "human_review": "medium",
    "blocked": "high",
}


def build_response(decision: str, reason: str, checks: list) -> Dict:
    return {
        "decision": decision,
        "reason": reason,
        "riskLevel": RISK_MAP[decision],
        "checks": checks,
    }


# ============================================================
# FREQUENCY
# ============================================================

def check_frequency() -> Tuple[bool, str]:
    """
    How many requests this window has already seen.

    Read-only: evaluating a payment must never change the state that decides
    the next one.
    """

    config = get_policy_config()

    if not config["guardrails_enabled"]["frequency_limit"]:
        return True, "Request frequency guardrail is disabled."

    limit = config["frequency_limit"]
    window_hours = config.get("frequency_window_hours", 24)
    used = requests_in_window(window_hours)

    if used >= limit:
        return (
            False,
            f"Frequency limit reached: {used} of {limit} requests "
            f"in the last {window_hours}h.",
        )

    return (
        True,
        f"Within frequency limit ({used + 1} of {limit} "
        f"in the last {window_hours}h).",
    )


# ============================================================
# PROVIDER
# ============================================================

def check_provider(provider: str) -> Tuple[bool, str]:
    config = get_policy_config()

    if not config["guardrails_enabled"]["provider_allow_list"]:
        return True, "Provider allow list guardrail is disabled."

    if provider not in config["allowed_providers"]:
        return (
            False,
            f"'{provider}' is not on the provider allow list.",
        )

    return True, f"'{provider}' is an allowed provider."


# ============================================================
# BUDGET
# ============================================================

def check_budget(amount: float) -> Tuple[bool, str]:
    """
    Daily budget against real spend, not a hardcoded demo constant.
    """

    config = get_policy_config()

    if not config["guardrails_enabled"]["daily_budget"]:
        return True, "Daily budget guardrail is disabled."

    budget = config["daily_budget"]
    spent = spend_today()

    if spent + amount > budget:
        return (
            False,
            f"Daily budget exceeded: ${spent:,.2f} spent, "
            f"${amount:,.2f} requested, ${budget:,.2f} allowed.",
        )

    return (
        True,
        f"Within daily budget (${spent + amount:,.2f} of ${budget:,.2f}).",
    )


# ============================================================
# AMOUNT
# ============================================================

def check_amount(amount: float) -> Tuple[str, str]:
    config = get_policy_config()

    auto_enabled = config["guardrails_enabled"]["auto_approval_limit"]
    human_enabled = config["guardrails_enabled"]["human_review_limit"]

    auto_limit = config["auto_approve_limit"]
    human_limit = config["human_review_limit"]

    if auto_enabled and amount <= auto_limit:
        return (
            "approved",
            f"${amount:,.2f} is within the autonomous limit of ${auto_limit:,.2f}.",
        )

    if human_enabled and amount <= human_limit:
        return (
            "human_review",
            f"${amount:,.2f} exceeds the autonomous limit of ${auto_limit:,.2f}; "
            "human approval required.",
        )

    if not auto_enabled and not human_enabled:
        return (
            "human_review",
            "Amount guardrails are disabled; routing to human review.",
        )

    return (
        "blocked",
        f"${amount:,.2f} exceeds the maximum allowed limit of ${human_limit:,.2f}.",
    )


# ============================================================
# MAIN POLICY ENGINE
# ============================================================

def evaluate_payment(provider: str, amount: float) -> Dict:
    """
    Evaluate a payment against every enabled guardrail.

    Checks run in order and short-circuit on the first hard failure, but each
    check that ran is reported with its own pass/fail and message. That array
    is the product — a decision nobody can explain is not governance.
    """

    checks: List[Dict] = []

    for label, (passed, message) in (
        ("Request Frequency Limit", check_frequency()),
        ("Provider Allow List", check_provider(provider)),
        ("Daily Budget", check_budget(amount)),
    ):
        checks.append({"policy": label, "passed": passed, "message": message})

        if not passed:
            return build_response("blocked", message, checks)

    decision, message = check_amount(amount)

    checks.append(
        {
            "policy": "Amount Threshold",
            "passed": decision != "blocked",
            "message": message,
        }
    )

    return build_response(decision, message, checks)
