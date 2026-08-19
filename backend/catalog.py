"""
Service catalog and intent resolution.

Two things changed from the original selector:

1. Files load from absolute paths, so the app starts from any working
   directory instead of only from backend/.

2. Resolution is cost-aware. The original always took `apis[category][0]`,
   which meant the most expensive listed option was chosen every time and the
   cheaper alternatives in the catalog were unreachable. A spend guard that
   always picks the priciest provider is a strange spend guard.

The catalog is also the boundary that makes the guard safe against injected
payment instructions: an agent names a *category* or a *known provider*. It
can never hand us a URL or a payee address, so "pay 0xdeadbeef, instructions
found in a document" has nowhere to enter the system.
"""

import json
from typing import Dict, List, Optional

import config


# ============================================================
# LOAD
# ============================================================

with open(config.API_CATALOG_FILE, "r", encoding="utf-8") as handle:
    APIS: Dict[str, List[dict]] = json.load(handle)

with open(config.KEYWORD_MAP_FILE, "r", encoding="utf-8") as handle:
    KEYWORDS: Dict[str, dict] = json.load(handle)


KNOWN_PROVIDERS = sorted(
    {entry["provider"] for entries in APIS.values() for entry in entries}
)


# ============================================================
# CATEGORY MATCHING
# ============================================================

def match_categories(prompt: str) -> List[dict]:
    """
    Every category whose keywords appear in the prompt, highest priority first.
    """

    text = (prompt or "").lower()
    matched: List[dict] = []

    for category, details in KEYWORDS.items():
        for keyword in details["keywords"]:
            if keyword in text:
                matched.append(
                    {
                        "category": category,
                        "priority": details["priority"],
                        "matchedOn": keyword,
                    }
                )
                break

    matched.sort(key=lambda item: item["priority"], reverse=True)

    return matched


def select_category(prompt: str) -> Optional[dict]:
    matched = match_categories(prompt)

    return matched[0] if matched else None


# ============================================================
# API SELECTION
# ============================================================

def cheapest_in_category(category: str) -> Optional[dict]:
    """
    Pick the lowest-cost service that satisfies the category.

    Ties keep catalog order, so the listed preference still wins among equals.
    """

    entries = APIS.get(category)

    if not entries:
        return None

    return min(entries, key=lambda entry: float(entry.get("cost", 0)))


def find_provider(provider: str, category: Optional[str] = None) -> Optional[dict]:
    """
    Look up a specific provider by name, optionally scoped to a category.

    Returns None for anything not in the catalog — which is how an injected
    "pay quickpay-services.net" instruction dies before it reaches policy.
    """

    if not provider:
        return None

    wanted = provider.strip().lower()
    search_space = (
        [(category, APIS.get(category, []))]
        if category
        else list(APIS.items())
    )

    for cat, entries in search_space:
        for entry in entries:
            if entry["provider"].strip().lower() == wanted:
                return {**entry, "category": cat}

    return None


def alternatives(category: str) -> List[dict]:
    """
    Everything available in a category, cheapest first — used to explain a
    decision ("we could have used X for $0").
    """

    entries = APIS.get(category, [])

    return sorted(entries, key=lambda entry: float(entry.get("cost", 0)))


def resolve_endpoint(provider: str, service: Optional[dict] = None) -> Optional[str]:
    """
    The URL the guard should call for a provider, if any.

    Checked in order: an AEGIS_ENDPOINT_<PROVIDER> environment variable, then
    an `endpoint` field on the catalog entry.

    Keeping this env-driven means a real upstream can be wired in without
    editing the catalog, and — importantly — that the live call path is
    reachable in tests against a local stub rather than being dead code that
    only runs in production.

    Returns None when no endpoint is configured, in which case the guard
    fulfils in simulation and says so.
    """

    import os

    key = (
        "AEGIS_ENDPOINT_"
        + provider.strip().upper().replace("-", "_").replace(".", "_").replace(" ", "_")
    )

    from_env = os.getenv(key, "").strip()

    if from_env:
        return from_env

    if service and service.get("endpoint"):
        return service["endpoint"]

    entry = find_provider(provider)

    return entry.get("endpoint") if entry else None


def describe_capabilities() -> Dict[str, List[dict]]:
    """
    What AEGIS can reach, for the graceful no-match response.
    """

    return {
        category: [
            {
                "provider": entry["provider"],
                "name": entry["name"],
                "cost": entry["cost"],
            }
            for entry in alternatives(category)
        ]
        for category in APIS
    }
