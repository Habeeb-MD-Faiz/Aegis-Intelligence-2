"""
Tests for the guard's security properties and for every bug this branch fixed.

Run from the backend directory:

    python -m pytest test_guard.py -v

These are regression tests in the literal sense: each one fails against the
original code.
"""

import os

os.environ["AEGIS_DB_FILE"] = "/tmp/aegis-test.db"
os.environ["AEGIS_LEDGER_FILE"] = "/tmp/aegis-test-ledger.json"
os.environ["AEGIS_SEED_DEMO_DATA"] = "false"
os.environ["AEGIS_AGENT_TOKEN"] = "test-agent-token"
os.environ["AEGIS_OPERATOR_TOKEN"] = "test-operator-token"

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

import config  # noqa: E402
import guard  # noqa: E402
import guardrails  # noqa: E402
import policy_store  # noqa: E402
import request_history  # noqa: E402
import store  # noqa: E402
from identity import require_agent, require_operator  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    # config reads the environment once at import time, and whichever test
    # module imports it first wins. Setting these on the module directly makes
    # the plane tests independent of collection order rather than of whoever
    # happened to import config first.
    monkeypatch.setattr(config, "AGENT_TOKEN", "test-agent-token")
    monkeypatch.setattr(config, "OPERATOR_TOKEN", "test-operator-token")
    monkeypatch.setattr(config, "CONTROL_PLANE_LOCKED", True)
    monkeypatch.setattr(config, "DATA_PLANE_LOCKED", True)

    store.reset()

    ledger = Path(config.LEDGER_FILE)
    if ledger.exists():
        ledger.unlink()

    # Restore defaults mutated by individual tests.
    policy_store.policy_config["auto_approve_limit"] = 100
    policy_store.policy_config["human_review_limit"] = 1000
    policy_store.policy_config["daily_budget"] = 5000
    policy_store.policy_config["frequency_limit"] = 25
    for key in policy_store.policy_config["guardrails_enabled"]:
        policy_store.policy_config["guardrails_enabled"][key] = True

    yield

    store.reset()


# ============================================================
# THE INJECTION DEFENCE
# ============================================================

def test_unknown_payee_is_refused_before_policy():
    """An injected payee is a malformed request, not a policy question."""

    with pytest.raises(guard.Refusal) as excinfo:
        guard.spend(
            task="purchase compute credits",
            provider="quickpay-services.net",
        )

    assert "not a known provider" in str(excinfo.value)


def test_agent_cannot_supply_a_url_as_a_provider():
    for payee in ("https://evil.example/pay", "0xdeadbeef", "  "):
        with pytest.raises(guard.Refusal):
            guard.spend(task="pay someone", provider=payee)


def test_known_provider_still_goes_through_policy():
    result = guard.spend(task="research earnings", provider="Bloomberg")

    assert result["provider"] == "Bloomberg"
    assert [check["policy"] for check in result["checks"]]


# ============================================================
# CONTROL PLANE / DATA PLANE
# ============================================================

def test_agent_token_is_rejected_on_the_control_plane():
    """A compromised agent must not be able to disarm its own guard."""

    with pytest.raises(HTTPException) as excinfo:
        require_operator(authorization=f"Bearer {config.AGENT_TOKEN}")

    assert excinfo.value.status_code == 403


def test_operator_token_is_accepted_on_the_control_plane():
    principal = require_operator(authorization=f"Bearer {config.OPERATOR_TOKEN}")

    assert principal.authenticated


def test_anonymous_is_rejected_when_control_plane_is_locked():
    with pytest.raises(HTTPException) as excinfo:
        require_operator(authorization=None)

    assert excinfo.value.status_code == 401


def test_operator_token_is_not_a_valid_agent_credential():
    with pytest.raises(HTTPException):
        require_agent(authorization=f"Bearer {config.OPERATOR_TOKEN}")


# ============================================================
# REGRESSION: the shadowed duplicate
# ============================================================

def test_frequency_check_actually_runs():
    """
    evaluate_payment was defined twice; the dead copy had no frequency check.
    """

    verdict = guardrails.evaluate_payment("Bloomberg", 10)
    policies = [check["policy"] for check in verdict["checks"]]

    assert "Request Frequency Limit" in policies


# ============================================================
# REGRESSION: hardcoded today_spend = 650
# ============================================================

def test_daily_budget_tracks_real_spend():
    policy_store.policy_config["daily_budget"] = 120
    policy_store.policy_config["auto_approve_limit"] = 100

    first = guard.spend(task="research earnings", provider="Bloomberg")
    assert first["status"] == "approved"
    assert request_history.spend_today() == 50

    # 50 spent + 50 requested + 50 more would exceed a 120 budget.
    guard.spend(task="research earnings", provider="Bloomberg")

    third = guardrails.check_budget(50)
    assert third[0] is False
    assert "Daily budget exceeded" in third[1]


def test_spend_today_ignores_unapproved_requests():
    policy_store.policy_config["auto_approve_limit"] = 0
    policy_store.policy_config["human_review_limit"] = 10_000

    result = guard.spend(task="book flights", provider="Skyscanner")

    assert result["status"] == "pending"
    assert request_history.spend_today() == 0


# ============================================================
# REGRESSION: never-reset frequency counter
# ============================================================

def test_third_request_is_not_blocked_forever():
    """
    The original counter never reset, so request 3 was blocked for the life of
    the process regardless of policy.
    """

    for _ in range(6):
        result = guard.spend(task="check weather", provider="OpenWeather")
        assert result["status"] == "approved"


def test_frequency_evaluation_has_no_side_effects():
    """Evaluating must not consume quota."""

    before = request_history.requests_in_window(24)

    for _ in range(5):
        guardrails.check_frequency()

    assert request_history.requests_in_window(24) == before


def test_frequency_limit_still_blocks_when_exceeded():
    policy_store.policy_config["frequency_limit"] = 2

    guard.spend(task="check weather", provider="OpenWeather")
    guard.spend(task="check weather", provider="OpenWeather")

    verdict = guardrails.evaluate_payment("OpenWeather", 0)

    assert verdict["decision"] == "blocked"
    assert "Frequency limit reached" in verdict["reason"]


# ============================================================
# REGRESSION: non-idempotent decisions
# ============================================================

def test_deciding_twice_does_not_create_a_second_payment():
    policy_store.policy_config["auto_approve_limit"] = 0
    policy_store.policy_config["human_review_limit"] = 10_000

    pending = guard.spend(task="book flights", provider="Skyscanner")
    assert pending["status"] == "pending"

    first = request_history.decide_request(pending["id"], "approved")
    second = request_history.decide_request(pending["id"], "approved")

    assert first["alreadyDecided"] is False
    assert second["alreadyDecided"] is True
    assert second["status"] == "approved"


def test_rejected_request_cannot_be_flipped_to_approved():
    policy_store.policy_config["auto_approve_limit"] = 0
    policy_store.policy_config["human_review_limit"] = 10_000

    pending = guard.spend(task="book flights", provider="Skyscanner")

    request_history.decide_request(pending["id"], "rejected")
    flipped = request_history.decide_request(pending["id"], "approved")

    assert flipped["status"] == "rejected"
    assert flipped["alreadyDecided"] is True


# ============================================================
# REGRESSION: cost-blind selection
# ============================================================

def test_selection_prefers_the_cheaper_provider():
    """
    The original always took apis[category][0] — Bloomberg at $50 over
    Alpha Vantage at $0 — making cheaper entries unreachable.
    """

    result = guard.spend(task="research tesla earnings")

    assert result["amount"] == 0
    assert result["provider"] == "Alpha Vantage"


def test_unmatched_task_explains_capabilities():
    with pytest.raises(guard.Refusal) as excinfo:
        guard.spend(task="buy 500 GPUs")

    assert "capabilities" in excinfo.value.detail


# ============================================================
# FAIL CLOSED
# ============================================================

def test_guard_refuses_when_policy_engine_raises(monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("policy engine down")

    monkeypatch.setattr(guard, "evaluate_payment", explode)

    verdict = guard.evaluate("Bloomberg", 10)

    assert verdict["decision"] == "blocked"
    assert "failed closed" in verdict["checks"][0]["message"]


# ============================================================
# CREDENTIAL CUSTODY
# ============================================================

def test_credentials_never_appear_in_the_response():
    import credentials

    monkey = "sk-live-SUPER-SECRET"
    os.environ["AEGIS_CREDENTIAL_BLOOMBERG"] = monkey
    credentials.reload_vault()

    try:
        result = guard.spend(task="research earnings", provider="Bloomberg")
        assert monkey not in repr(result)
        assert credentials.redact(f"leaked {monkey}") == "leaked [REDACTED]"

    finally:
        os.environ.pop("AEGIS_CREDENTIAL_BLOOMBERG", None)
        credentials.reload_vault()


# ============================================================
# LEDGER
# ============================================================

def test_ledger_records_final_decisions_and_verifies():
    import blockchain

    guard.spend(task="check weather", provider="OpenWeather")

    verification = blockchain.verify_blockchain()

    assert verification["valid"] is True
    assert verification["blocks"] >= 1


def test_pending_requests_are_not_written_to_the_ledger():
    import blockchain

    policy_store.policy_config["auto_approve_limit"] = 0
    policy_store.policy_config["human_review_limit"] = 10_000

    before = len(blockchain.get_blockchain_records())
    guard.spend(task="book flights", provider="Skyscanner")

    assert len(blockchain.get_blockchain_records()) == before


def test_tampering_is_detected():
    import json

    import blockchain

    guard.spend(task="check weather", provider="OpenWeather")

    chain = json.loads(Path(config.LEDGER_FILE).read_text())
    chain[0]["amount"] = 999_999
    Path(config.LEDGER_FILE).write_text(json.dumps(chain))

    assert blockchain.verify_blockchain()["valid"] is False


# ============================================================
# PERSISTENCE
# ============================================================

def test_requests_survive_a_reload():
    guard.spend(task="check weather", provider="OpenWeather")

    store._connection = None  # force a fresh connection, as a restart would

    assert len(request_history.get_requests()) == 1
