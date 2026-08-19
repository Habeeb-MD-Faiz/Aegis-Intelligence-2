"""
Risk scoring.

The deck used to claim LLM-driven "risk assessment". It wasn't true: riskLevel
was a static lookup from the decision (approved→low, review→medium,
blocked→high), which is a relabeling, not an assessment.

This makes the claim true — but deliberately *without* an LLM. Enforcement
must be explainable and reproducible: the same request must score the same way
twice, and an operator must be able to see exactly which signal fired. A
probabilistic model deciding whether to release money is the thing AEGIS
exists to prevent.

Signals are behavioural and computed from the agent's own history:

  first-time provider    an agent paying someone it has never paid before
  spend deviation        an amount far above this agent's normal
  velocity               a burst of requests in a short window
  novel category         spending in a category this agent has never used
  recent refusals        an agent that has just been blocked repeatedly

Each returns a score contribution and a human-readable reason. The total maps
to low / medium / high. The policy decision is separate and always wins — risk
annotates a decision, it does not make one.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from request_history import get_requests


# ============================================================
# TUNING
# ============================================================

FIRST_TIME_PROVIDER_SCORE = 25
NOVEL_CATEGORY_SCORE = 15
DEVIATION_SCORE = 30
VELOCITY_SCORE = 20
REFUSAL_SCORE = 25

VELOCITY_WINDOW_MINUTES = 10
VELOCITY_THRESHOLD = 5

REFUSAL_WINDOW_MINUTES = 30
REFUSAL_THRESHOLD = 2

# An amount this many times the agent's average is treated as a deviation.
DEVIATION_MULTIPLE = 3.0

MEDIUM_AT = 25
HIGH_AT = 50


def _parse(timestamp: str) -> Optional[datetime]:
    if not timestamp:
        return None

    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    except ValueError:
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _history_for(agent_id: str) -> List[Dict]:
    """
    Prior requests from this agent. Falls back to global history for an
    unidentified agent, which is the conservative reading.
    """

    requests = get_requests()

    if not agent_id or agent_id == "unidentified-agent":
        return requests

    scoped = [r for r in requests if r.get("agentId") == agent_id]

    return scoped if scoped else requests


# ============================================================
# SIGNALS
# ============================================================

def _first_time_provider(history: List[Dict], provider: str) -> Optional[Dict]:
    if any(r.get("provider") == provider for r in history):
        return None

    return {
        "signal": "first_time_provider",
        "score": FIRST_TIME_PROVIDER_SCORE,
        "message": f"First payment to '{provider}' from this agent.",
    }


def _novel_category(history: List[Dict], category: Optional[str]) -> Optional[Dict]:
    if not category:
        return None

    if any(r.get("category") == category for r in history):
        return None

    return {
        "signal": "novel_category",
        "score": NOVEL_CATEGORY_SCORE,
        "message": f"First spend in the '{category}' category from this agent.",
    }


def _spend_deviation(history: List[Dict], amount: float) -> Optional[Dict]:
    amounts = []

    for record in history:
        try:
            value = float(record.get("amount", 0))

        except (TypeError, ValueError):
            continue

        if value > 0:
            amounts.append(value)

    if len(amounts) < 3 or amount <= 0:
        return None

    average = sum(amounts) / len(amounts)

    if average <= 0 or amount < average * DEVIATION_MULTIPLE:
        return None

    return {
        "signal": "spend_deviation",
        "score": DEVIATION_SCORE,
        "message": (
            f"${amount:,.2f} is {amount / average:.1f}x this agent's "
            f"average of ${average:,.2f}."
        ),
    }


def _velocity(history: List[Dict]) -> Optional[Dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=VELOCITY_WINDOW_MINUTES)
    recent = 0

    for record in history:
        created = _parse(record.get("createdAt", ""))

        if created and created >= cutoff:
            recent += 1

    if recent < VELOCITY_THRESHOLD:
        return None

    return {
        "signal": "velocity",
        "score": VELOCITY_SCORE,
        "message": (
            f"{recent} requests in the last {VELOCITY_WINDOW_MINUTES} minutes."
        ),
    }


def _recent_refusals(history: List[Dict]) -> Optional[Dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=REFUSAL_WINDOW_MINUTES)
    refused = 0

    for record in history:
        if record.get("status") != "rejected":
            continue

        created = _parse(record.get("createdAt", ""))

        if created and created >= cutoff:
            refused += 1

    if refused < REFUSAL_THRESHOLD:
        return None

    return {
        "signal": "recent_refusals",
        "score": REFUSAL_SCORE,
        "message": (
            f"{refused} refused requests from this agent in the last "
            f"{REFUSAL_WINDOW_MINUTES} minutes."
        ),
    }


# ============================================================
# SCORING
# ============================================================

def assess(
    agent_id: str,
    provider: str,
    amount: float,
    category: Optional[str] = None,
) -> Dict:
    """
    Score a request before it is decided.

    Returns a level, a 0-100 score, and the signals that fired with reasons.
    An empty signal list means nothing unusual was observed — which is itself
    worth showing, rather than an unexplained "low".
    """

    history = _history_for(agent_id)

    signals = [
        signal
        for signal in (
            _first_time_provider(history, provider),
            _novel_category(history, category),
            _spend_deviation(history, amount),
            _velocity(history),
            _recent_refusals(history),
        )
        if signal is not None
    ]

    score = min(100, sum(signal["score"] for signal in signals))

    if score >= HIGH_AT:
        level = "high"
    elif score >= MEDIUM_AT:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "score": score,
        "signals": signals,
        "observations": len(history),
        "summary": (
            "; ".join(signal["message"] for signal in signals)
            if signals
            else "No unusual behaviour observed for this agent."
        ),
    }


def combine(policy_decision: str, assessment: Dict) -> str:
    """
    Reconcile the behavioural score with the policy decision.

    Policy always wins on the downside — a blocked payment is high risk no
    matter how ordinary it looked, and an escalated one is never "low". Risk
    can raise a level but never lower one below what the decision implies.
    """

    floor = {"approved": "low", "human_review": "medium", "blocked": "high"}
    order = ["low", "medium", "high"]

    baseline = floor.get(policy_decision, "medium")

    return max(baseline, assessment["level"], key=order.index)
