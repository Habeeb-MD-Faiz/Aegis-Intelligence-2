"""
Control plane / data plane separation.

The question this file exists to answer:

    "If the agent is prompt-injected, what stops it calling your API and
     turning the guardrails off?"

Answer: policy mutation lives on a different plane, behind a different
credential, and an agent credential can never authorize it. A compromised
agent can submit spend intents and nothing else.

The separation is structural. Even in open demo mode, presenting an agent
token to a control-plane route is rejected — the planes are not merely
differently-configured, they are different credential types.
"""

from enum import Enum
from typing import Optional

from fastapi import Header, HTTPException

import config


class Plane(str, Enum):
    CONTROL = "control"
    DATA = "data"


class Principal:
    """
    Who is making this request, and on which plane.
    """

    def __init__(self, plane: Plane, name: str, authenticated: bool):
        self.plane = plane
        self.name = name
        self.authenticated = authenticated

    def __repr__(self) -> str:
        return (
            f"Principal(plane={self.plane.value}, "
            f"name={self.name!r}, authenticated={self.authenticated})"
        )


def _header_value(raw) -> str:
    """
    Normalize a header argument to a string.

    When these functions are called directly — from tests, or from the demo
    script — FastAPI's dependency injection has not run, so an unfilled
    parameter still holds its `Header(...)` default object rather than a
    string. Treat anything that is not a string as absent.
    """

    return raw.strip() if isinstance(raw, str) else ""


def _extract(authorization: Optional[str]) -> str:
    """
    Pull the token out of an Authorization header.

    Accepts both "Bearer <token>" and a bare token.
    """

    value = _header_value(authorization)

    if not value:
        return ""

    if value.lower().startswith("bearer "):
        return value[7:].strip()

    return value


# ============================================================
# CONTROL PLANE — operators only
# ============================================================

def require_operator(
    authorization: Optional[str] = Header(default=None),
) -> Principal:
    """
    Guards every route that can change what the guard enforces.

    Presenting the agent token here is always rejected, even when the control
    plane is otherwise open. That is the point: an agent must never be able to
    widen its own authority.
    """

    token = _extract(authorization)

    # An agent credential is never valid on the control plane.
    if config.AGENT_TOKEN and token and token == config.AGENT_TOKEN:
        raise HTTPException(
            status_code=403,
            detail=(
                "Agent credentials cannot modify policy. "
                "Policy changes require an operator credential."
            ),
        )

    if not config.CONTROL_PLANE_LOCKED:
        # Demo mode: no operator token configured, so the plane is open.
        # /config reports this so the UI can display it honestly.
        return Principal(Plane.CONTROL, "anonymous-operator", authenticated=False)

    if token != config.OPERATOR_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Operator credential required for policy changes.",
        )

    return Principal(Plane.CONTROL, "operator", authenticated=True)


# ============================================================
# DATA PLANE — agents only
# ============================================================

def require_agent(
    authorization: Optional[str] = Header(default=None),
    x_agent_id: Optional[str] = Header(default=None),
) -> Principal:
    """
    Guards the routes agents use to submit spend intents.

    The operator token is deliberately *not* accepted as a substitute — an
    operator credential leaking into an agent process should not silently grant
    it a working data-plane identity.
    """

    token = _extract(authorization)
    agent_name = _header_value(x_agent_id) or "unidentified-agent"

    if not config.DATA_PLANE_LOCKED:
        return Principal(Plane.DATA, agent_name, authenticated=False)

    if token != config.AGENT_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Agent credential required.",
        )

    return Principal(Plane.DATA, agent_name, authenticated=True)
