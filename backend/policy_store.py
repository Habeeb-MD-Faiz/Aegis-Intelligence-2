"""
Active policy configuration.

Two changes:

- The frequency counter that lived here is gone. It incremented during
  evaluation and nothing ever reset it, so the third request in a process
  lifetime was blocked forever. Frequency is now derived from request
  timestamps in guardrails.py, which needs no counter and no reset.

- `apply_policy_suggestion` no longer rejects a legitimate suggested value of
  "0" (the old `if not suggested_value` guard treated it as missing), and
  parses values defensively so a malformed suggestion returns a clear error
  instead of a 500.
"""

from typing import Dict


# ============================================================
# ACTIVE CONFIGURATION
# ============================================================

policy_config: Dict = {
    "allowed_providers": [
        "Bloomberg",
        "NewsAPI",
        "Skyscanner",
        "OpenWeather",
        "Gmail",
        "Alpha Vantage",
        "Google",
    ],

    "auto_approve_limit": 100,
    "human_review_limit": 1000,
    "daily_budget": 5000,

    "frequency_limit": 25,
    "frequency_window_hours": 24,

    "guardrails_enabled": {
        "provider_allow_list": True,
        "auto_approval_limit": True,
        "human_review_limit": True,
        "daily_budget": True,
        "frequency_limit": True,
    },
}


def get_policy_config() -> Dict:
    return policy_config


# ============================================================
# GUARDRAIL TOGGLES
# ============================================================

def toggle_guardrail(guardrail_id: str, enabled: bool) -> Dict:
    if guardrail_id not in policy_config["guardrails_enabled"]:
        raise ValueError(f"Unknown guardrail: {guardrail_id}")

    policy_config["guardrails_enabled"][guardrail_id] = enabled

    return policy_config


# ============================================================
# APPLY AN AI SUGGESTION
# ============================================================

def _parse_money(raw) -> float:
    """
    Suggestions arrive as display strings like "$1,500". Parse defensively so a
    malformed value becomes a clean error rather than an unhandled exception.
    """

    if isinstance(raw, (int, float)):
        return float(raw)

    text = str(raw).strip().replace("$", "").replace(",", "")

    try:
        return float(text)

    except ValueError as exc:
        raise ValueError(f"Could not read a number from {raw!r}.") from exc


# The four suggestion types that map to a single scalar setting. Keyed by the
# type the LLM is allowed to emit, so this table and the Literal in
# policy_builder.PolicySuggestion can be read against each other — an earlier
# version had them drift, and the schema advertised two types that landed here
# as "Unsupported policy suggestion type" when an operator clicked Apply.
_SCALAR_SETTINGS = {
    "spending_limit": (
        "auto_approve_limit",
        _parse_money,
        "Autonomous approval limit updated to ${:,.0f}.",
    ),
    "daily_budget": (
        "daily_budget",
        _parse_money,
        "Daily budget updated to ${:,.0f}.",
    ),
    "frequency_limit": (
        "frequency_limit",
        lambda raw: int(_parse_money(raw)),
        "Frequency limit updated to {:,.0f} requests.",
    ),
}


def apply_policy_suggestion(suggestion: dict) -> Dict:
    """
    Apply an operator-approved policy suggestion.

    Suggestions never apply themselves — this is only ever reached from a
    control-plane route behind an operator credential.
    """

    suggestion_type = suggestion.get("suggestion_type")
    suggested_value = suggestion.get("suggested_value")

    # Note: an explicit "0" is a legitimate value, so this checks for absence
    # rather than falsiness.
    if suggested_value is None or str(suggested_value).strip() == "":
        raise ValueError("Suggestion does not contain a value.")

    # The allow list is the one type that appends to a collection rather than
    # replacing a scalar, and the one that can be a no-op.
    if suggestion_type == "provider_allowlist":
        provider = str(suggested_value).strip()

        if provider in policy_config["allowed_providers"]:
            return {
                "success": True,
                "message": f"{provider} is already on the allow list.",
                "config": policy_config,
            }

        policy_config["allowed_providers"].append(provider)

        return {
            "success": True,
            "message": f"{provider} added to the provider allow list.",
            "config": policy_config,
        }

    if suggestion_type in _SCALAR_SETTINGS:
        key, parse, message = _SCALAR_SETTINGS[suggestion_type]
        value = parse(suggested_value)
        policy_config[key] = value

        return {
            "success": True,
            "message": message.format(value),
            "config": policy_config,
        }

    raise ValueError(f"Unsupported policy suggestion type: {suggestion_type}")
