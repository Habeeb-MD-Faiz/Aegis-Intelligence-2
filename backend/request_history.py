"""
Request history and the derived figures the policy engine depends on.

Changes from the original:

- Records persist to SQLite instead of a module-level list, so history (and
  therefore the audit trail) survives a restart.

- `decide_request` is now idempotent. It previously re-decided requests that
  were already final, which created a second payment and a second transaction
  ID on every repeat call while the ledger deduplicated and recorded only one
  — leaving the payment store and the audit trail disagreeing about what
  happened.

- Added `spend_today` and `requests_in_window`, which let the budget and
  frequency guardrails measure reality instead of hardcoded constants.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import uuid4

import store
from blockchain import create_blockchain_record


FINAL_STATUSES = {"approved", "rejected"}


# ============================================================
# TIME HELPERS
# ============================================================

def _now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(timestamp: str) -> Optional[datetime]:
    """
    Read a record's `createdAt` into an aware datetime, or None if unreadable.

    This is the *only* timestamp parser in the codebase, and deliberately so:
    risk.py imports it rather than keeping its own copy. The module that
    records spend and the module that scores it must never disagree about what
    a timestamp means, or about where the day boundary falls.

    The `.replace("Z", ...)` is redundant on Python 3.11+, which parses a
    trailing Z natively. It is kept because it is free and the deploy target's
    runtime is not pinned.
    """

    if not timestamp:
        return None

    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


# ============================================================
# WRITE
# ============================================================

def add_request(request: Dict) -> Dict:
    if "id" not in request:
        request["id"] = str(uuid4())

    request.setdefault("createdAt", _now().isoformat())

    store.save_request(request)

    return request


# ============================================================
# READ
# ============================================================

def get_requests() -> List[Dict]:
    return store.load_requests()


# ============================================================
# DERIVED FIGURES
# ============================================================

def _since(cutoff: datetime, status: Optional[str] = None) -> List[Dict]:
    """
    Records created at or after `cutoff`, optionally filtered by status.

    Both derived figures share this traversal so a change to how a record's
    timestamp is read cannot make the budget and the frequency window disagree
    about which requests are in scope. The *filters* stay different on purpose
    — see each caller.
    """

    selected = []

    for request in get_requests():
        if status is not None and request.get("status") != status:
            continue

        created = parse_timestamp(request.get("createdAt", ""))

        if created is None or created < cutoff:
            continue

        selected.append(request)

    return selected


def spend_today() -> float:
    """
    Total approved spend in the current UTC day.

    This replaces `today_spend = 650`, which meant the daily budget guardrail
    never observed a single real transaction.
    """

    start_of_day = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    total = 0.0

    for request in _since(start_of_day, status="approved"):
        try:
            total += float(request.get("amount", 0))

        except (TypeError, ValueError):
            continue

    return total


def requests_in_window(hours: int = 24) -> int:
    """
    How many requests were submitted in the trailing window.

    Counts *every* status, unlike spend_today — a refused request still
    consumed a slot in the frequency window. Derived from timestamps rather
    than a counter, so it self-heals over time and needs no reset endpoint or
    scheduled job.
    """

    return len(_since(_now() - timedelta(hours=hours)))


# ============================================================
# DECISIONS
# ============================================================

def decide_request(request_id: str, decision: str) -> Optional[Dict]:
    """
    Apply a human decision to a pending request.

    Idempotent by design: a request that has already reached a final status is
    returned unchanged rather than decided twice. Callers can tell the
    difference through the `alreadyDecided` flag.
    """

    if decision not in FINAL_STATUSES:
        return None

    request = store.load_request(request_id)

    if request is None:
        return None

    if request.get("status") in FINAL_STATUSES:
        return {**request, "alreadyDecided": True}

    request["status"] = decision
    request["decisionBy"] = "User"
    request["decidedAt"] = _now().isoformat()

    store.save_request(request)

    # The ledger records the decision that was actually made, once it is final.
    create_blockchain_record(request)

    return {**request, "alreadyDecided": False}


# ============================================================
# DASHBOARD
# ============================================================

def get_dashboard_stats() -> Dict:
    requests = get_requests()

    def count(status: str) -> int:
        return sum(1 for item in requests if item.get("status") == status)

    return {
        "totalRequests": len(requests),
        "pending": count("pending"),
        "approved": count("approved"),
        "rejected": count("rejected"),
        "todaySpend": spend_today(),
    }
