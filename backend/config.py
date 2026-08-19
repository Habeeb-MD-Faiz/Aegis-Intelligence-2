"""
Central configuration for AEGIS.

Everything that used to be a hardcoded constant scattered across modules now
lives here and can be overridden with an environment variable, so the same
code runs locally, in CI and on Render without edits.
"""

import os
from pathlib import Path


# ============================================================
# PATHS
# ============================================================
#
# These are absolute and derived from this file's location.
#
# Previously selector.py opened "api_catalog.json" with a relative path, which
# meant the whole application only started if the working directory happened to
# be backend/. It now works from anywhere.

BASE_DIR = Path(__file__).resolve().parent

API_CATALOG_FILE = BASE_DIR / "api_catalog.json"
KEYWORD_MAP_FILE = BASE_DIR / "keyword_map.json"
LEDGER_FILE = Path(os.getenv("AEGIS_LEDGER_FILE", BASE_DIR / "blockchain.json"))
DATABASE_FILE = Path(os.getenv("AEGIS_DB_FILE", BASE_DIR / "aegis.db"))


# ============================================================
# HELPERS
# ============================================================

def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "").strip()

    if not raw:
        return default

    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()

    if not raw:
        return default

    return raw in {"1", "true", "yes", "on"}


# ============================================================
# HTTP
# ============================================================

CORS_ORIGINS = _env_list(
    "AEGIS_CORS_ORIGINS",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "https://aegis-frontend-oive.onrender.com",
    ],
)


# ============================================================
# IDENTITY — control plane vs data plane
# ============================================================
#
# AEGIS has two planes and they must never share a credential:
#
#   Control plane (operator)  — edit policy, toggle guardrails, apply
#                               suggestions. Humans only.
#
#   Data plane (agent)        — submit spend intents through the guard.
#                               Agents only.
#
# The separation is enforced in code regardless of whether tokens are
# configured: an agent credential can never authorize a control-plane route.
# Setting the two variables below additionally closes the planes to anonymous
# callers, which is what you want anywhere real.

OPERATOR_TOKEN = os.getenv("AEGIS_OPERATOR_TOKEN", "").strip()
AGENT_TOKEN = os.getenv("AEGIS_AGENT_TOKEN", "").strip()

# When no operator token is configured the control plane stays open so the
# public demo keeps working. The API reports this state so the UI can show it
# honestly rather than implying a security posture it does not have.
CONTROL_PLANE_LOCKED = bool(OPERATOR_TOKEN)
DATA_PLANE_LOCKED = bool(AGENT_TOKEN)


# ============================================================
# GUARD
# ============================================================
#
# Outbound calls the guard is willing to make on an agent's behalf. An agent
# can only name a provider from the catalog; it can never supply a raw URL,
# which is what stops "pay this address I found in a document".

GUARD_REQUEST_TIMEOUT = float(os.getenv("AEGIS_GUARD_TIMEOUT", "10"))

# Fail closed: if the policy engine raises, refuse rather than allow.
GUARD_FAIL_OPEN = _env_bool("AEGIS_GUARD_FAIL_OPEN", False)


# ============================================================
# LEDGER ANCHORING (Base Sepolia)
# ============================================================
#
# Optional. When an RPC URL and key are present, AEGIS periodically writes the
# ledger's chain head to Base Sepolia, so rewriting local history requires
# altering a record we do not control.
#
# Absent configuration, anchoring is skipped and the API says so. We never
# claim an anchor we did not write.

CHAIN_RPC_URL = os.getenv("AEGIS_CHAIN_RPC_URL", "https://sepolia.base.org").strip()
CHAIN_PRIVATE_KEY = os.getenv("AEGIS_CHAIN_PRIVATE_KEY", "").strip()
CHAIN_EXPLORER = os.getenv(
    "AEGIS_CHAIN_EXPLORER",
    "https://sepolia.basescan.org/tx/",
).strip()
CHAIN_NAME = os.getenv("AEGIS_CHAIN_NAME", "Base Sepolia").strip()

ANCHORING_ENABLED = bool(CHAIN_PRIVATE_KEY)

# Anchor after this many new blocks. 1 = anchor every decision.
ANCHOR_EVERY = int(os.getenv("AEGIS_ANCHOR_EVERY", "5"))


# ============================================================
# LLM
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
POLICY_MODEL = os.getenv("AEGIS_POLICY_MODEL", "llama-3.3-70b-versatile").strip()
LLM_ENABLED = bool(GROQ_API_KEY)


# ============================================================
# DEMO SEEDING
# ============================================================
#
# A cold Render dyno used to serve an empty dashboard. Seeding a handful of
# historical decisions at startup means the demo always has something to show.

SEED_DEMO_DATA = _env_bool("AEGIS_SEED_DEMO_DATA", True)


def public_config() -> dict:
    """
    Non-secret configuration, safe to expose to the frontend.
    """

    return {
        "controlPlaneLocked": CONTROL_PLANE_LOCKED,
        "dataPlaneLocked": DATA_PLANE_LOCKED,
        "anchoringEnabled": ANCHORING_ENABLED,
        "chainName": CHAIN_NAME,
        "llmEnabled": LLM_ENABLED,
        "guardFailOpen": GUARD_FAIL_OPEN,
    }
