"""
Policy Builder — the system reads its own decision history and proposes
amendments to the rules that govern it.

Governance systems die of staleness: thresholds get set once, drift out of
date, and people route around them. This closes that loop, with a human in it.

Suggestions are typed, evidence-backed, and never self-applying. Applying one
is a separate action on the control plane behind an operator credential — a
governance system that rewrites its own rules unsupervised is precisely the
failure mode AEGIS exists to prevent.

Note on initialisation: the LLM client is built lazily. It used to be
constructed at import time, which meant a missing GROQ_API_KEY did not degrade
this one feature — it crashed the entire API at boot, taking all twenty
endpoints with it.
"""

import json
from typing import List, Literal, Optional

from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel, Field

import config
from request_history import get_requests


# ============================================================
# STRUCTURED LLM OUTPUT
# ============================================================

class PolicySuggestion(BaseModel):
    suggestion_type: Literal[
        "spending_limit",
        "provider_allowlist",
        "frequency_limit",
        "category_limit",
        "daily_budget",
        "risk_rule",
    ]

    title: str

    category: Optional[str] = None

    current_value: Optional[str] = None

    suggested_value: Optional[str] = None

    reason: str

    confidence: int = Field(
        ge=0,
        le=100
    )

    evidence_count: int

    recommendation: Literal[
        "tighten",
        "relax",
        "add",
        "remove",
        "monitor"
    ]


class PolicySuggestionsResponse(BaseModel):
    suggestions: List[PolicySuggestion]


# ============================================================
# LLM
# ============================================================

_structured_llm = None


def _get_llm():
    """
    Build the structured LLM client on first use.

    Raises RuntimeError rather than crashing the process, so the caller can
    return a clean "policy suggestions unavailable" instead of a 500 — and so
    the rest of AEGIS runs perfectly well without an LLM key.
    """

    global _structured_llm

    if _structured_llm is not None:
        return _structured_llm

    if not config.LLM_ENABLED:
        raise RuntimeError(
            "Policy suggestions need GROQ_API_KEY. "
            "Every other part of AEGIS runs without it."
        )

    try:
        from langchain_groq import ChatGroq

    except ImportError as exc:
        raise RuntimeError(
            "langchain-groq is not installed; policy suggestions unavailable."
        ) from exc

    llm = ChatGroq(model=config.POLICY_MODEL, temperature=0)
    _structured_llm = llm.with_structured_output(PolicySuggestionsResponse)

    return _structured_llm


# ============================================================
# ANALYZE REQUEST HISTORY
# ============================================================

def generate_policy_suggestions():

    requests = get_requests()

    if not requests:
        return {
            "suggestions": [],
            "message": "Not enough request history to generate policy suggestions."
        }

    # We don't need to send unnecessary fields to the LLM.
    request_data = []

    for request in requests:

        request_data.append({
            "task": request.get("task"),
            "provider": request.get("provider"),
            "amount": request.get("amount"),
            "category": request.get("category"),
            "status": request.get("status"),
            "decision": request.get("decision"),
            "decisionBy": request.get("decisionBy"),
            "riskLevel": request.get("riskLevel"),
            "reason": request.get("reason"),
        })

    request_json = json.dumps(
        request_data,
        indent=2
    )

    prompt = f"""
You are the Policy Builder AI for AEGIS.

AEGIS is a governance system that controls autonomous AI-agent
payments and API spending.

Your job is NOT to approve or reject payments.

Your job is to analyze historical payment decisions and recommend
useful governance policy improvements.

Analyze the following request history:

{request_json}

Look for meaningful patterns such as:

1. Repeated successful requests from the same provider.
2. Repeated human approvals for amounts above the current
   autonomous threshold.
3. Repeated rejected providers.
4. Unusual transaction frequency.
5. Categories where spending limits may be too restrictive.
6. Categories where spending limits may be too permissive.
7. Repeated policy violations.
8. Repeated high-risk transactions.
9. Potential daily budget problems.

IMPORTANT:

- Do not invent evidence.
- Only make suggestions supported by the request history.
- Do not recommend changes based on a single insignificant event
  unless it represents an obvious security concern.
- Prefer conservative recommendations.
- Never directly execute a policy change.
- Suggestions will be reviewed by a human before being applied.
- If there is not enough evidence for a meaningful suggestion,
  return an empty list.

For every suggestion provide:

- suggestion_type
- title
- category if relevant
- current_value if known
- suggested_value
- reason
- confidence from 0 to 100
- evidence_count
- recommendation

Focus on actionable governance improvements.
"""

    try:
        structured_llm = _get_llm()

    except RuntimeError as exc:
        return {"suggestions": [], "message": str(exc)}

    try:
        result = structured_llm.invoke(prompt)

    except Exception as exc:  # noqa: BLE001
        return {
            "suggestions": [],
            "message": f"Policy suggestion generation failed: {exc}",
        }

    return result.model_dump()