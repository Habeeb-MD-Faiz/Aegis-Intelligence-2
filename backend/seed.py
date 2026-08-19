"""
Demo seeding.

A cold Render dyno used to serve an empty dashboard, so judges opening the
link before the pitch saw nothing at all.

Seeded records are dated to previous days on purpose. They give the dashboard
and the policy builder something real to work with, without consuming today's
budget or the current frequency window — so a seeded deployment behaves
exactly like an empty one for any decision made during the demo.

Seeding is idempotent and skipped entirely when history already exists.
"""

from datetime import datetime, timedelta, timezone
from typing import List
from uuid import uuid4

import config
import store


def _days_ago(days: int, hour: int = 10) -> str:
    moment = datetime.now(timezone.utc) - timedelta(days=days)

    return moment.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()


def _record(
    task: str,
    provider: str,
    api: str,
    amount: float,
    category: str,
    status: str,
    decision: str,
    reason: str,
    risk: str,
    decided_by: str,
    days: int,
) -> dict:
    return {
        "id": str(uuid4()),
        "task": task,
        "provider": provider,
        "api": api,
        "amount": amount,
        "category": category,
        "agentId": "seed-agent",
        "decision": decision,
        "riskLevel": risk,
        "reason": reason,
        "status": status,
        "decisionBy": decided_by,
        "createdAt": _days_ago(days),
        "checks": [],
        "seeded": True,
    }


def demo_records() -> List[dict]:
    """
    A history with enough shape for the policy builder to find real patterns:
    repeated human approvals of the same over-limit provider, a rejected
    provider, and routine low-value traffic.
    """

    return [
        _record(
            "research tesla quarterly earnings",
            "Bloomberg", "Bloomberg Market Data", 50, "research",
            "approved", "approved",
            "$50.00 is within the autonomous limit of $100.00.",
            "low", "Guardrails", 6,
        ),
        _record(
            "analyze semiconductor market trends",
            "Bloomberg", "Bloomberg Market Data", 50, "research",
            "approved", "approved",
            "$50.00 is within the autonomous limit of $100.00.",
            "low", "Guardrails", 5,
        ),
        _record(
            "book flights from delhi to singapore",
            "Skyscanner", "Skyscanner Flight Search", 150, "travel",
            "approved", "human_review",
            "$150.00 exceeds the autonomous limit of $100.00; human approval required.",
            "medium", "User", 5,
        ),
        _record(
            "find hotel options for the singapore trip",
            "Skyscanner", "Skyscanner Flight Search", 150, "travel",
            "approved", "human_review",
            "$150.00 exceeds the autonomous limit of $100.00; human approval required.",
            "medium", "User", 4,
        ),
        _record(
            "generate marketing images for launch",
            "OpenAI", "DALL-E Image Generation", 80, "image_generation",
            "rejected", "blocked",
            "'OpenAI' is not on the provider allow list.",
            "high", "Guardrails", 3,
        ),
        _record(
            "check weather for the delhi office",
            "OpenWeather", "OpenWeather Current", 0, "weather",
            "approved", "approved",
            "$0.00 is within the autonomous limit of $100.00.",
            "low", "Guardrails", 2,
        ),
        _record(
            "arrange airport transfer quotes",
            "Skyscanner", "Skyscanner Flight Search", 150, "travel",
            "approved", "human_review",
            "$150.00 exceeds the autonomous limit of $100.00; human approval required.",
            "medium", "User", 1,
        ),
    ]


def ensure_demo_data() -> int:
    """
    Seed demo history if the store is empty. Returns how many records written.
    """

    if not config.SEED_DEMO_DATA:
        return 0

    if store.load_requests():
        return 0

    records = demo_records()

    for record in records:
        store.save_request(record)

    print(f"🌱 Seeded {len(records)} historical requests for the demo.")

    return len(records)
