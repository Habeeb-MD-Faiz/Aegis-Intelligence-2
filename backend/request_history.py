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


def _parse(timestamp: str) -> Optional[datetime]:
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


def get_request(request_id: str) -> Optional[Dict]:
    return store.load_request(request_id)


# ============================================================
# DERIVED FIGURES
# ============================================================

def spend_today() -> float:
    """
    Total approved spend in the current UTC day.

    This replaces `today_spend = 650`, which meant the daily budget guardrail
    never observed a single real transaction.
    """

    start_of_day = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    total = 0.0

    for request in get_requests():
        if request.get("status") != "approved":
            continue

        created = _parse(request.get("createdAt", ""))

        if created is None or created < start_of_day:
            continue

        try:
            total += float(request.get("amount", 0))

        except (TypeError, ValueError):
            continue

    return total


def requests_in_window(hours: int = 24) -> int:
    """
    How many requests were submitted in the trailing window.

    Derived from timestamps rather than a counter, so it self-heals over time
    and needs no reset endpoint or scheduled job.
    """

    cutoff = _now() - timedelta(hours=hours)
    count = 0

    for request in get_requests():
        created = _parse(request.get("createdAt", ""))

        if created is not None and created >= cutoff:
            count += 1

    return count


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


def update_request(request_id: str, status: str, decision_by: str) -> Optional[Dict]:
    request = store.load_request(request_id)

    if request is None:
        return None

    request["status"] = status
    request["decisionBy"] = decision_by

    store.save_request(request)

    return request


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
