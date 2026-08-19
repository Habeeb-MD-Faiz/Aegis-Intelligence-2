"""
Task submission — the legacy entry point, now a thin wrapper over the guard.

This used to contain its own copy of the decide-record-pay sequence, which
meant `/execute-task` and any newer route could drift apart and enforce
subtly different policy. Everything now funnels through guard.spend(), so
there is exactly one path money can take.

Behaviour changes inherited from the guard:

- Unmatched tasks return a helpful response listing what AEGIS can actually
  reach, instead of a bare "Could not determine the task category." A judge
  typing "buy 500 GPUs" now gets an answer rather than an error.

- Service selection is cost-aware rather than always taking the first catalog
  entry, so the cheaper alternatives are reachable.
"""

from typing import Dict

import catalog
import guard


def select_api(user_prompt: str) -> Dict:
    """
    Submit a task to AEGIS and return the guard's decision.
    """

    try:
        return guard.spend(task=user_prompt, agent_id="task-console")

    except guard.Refusal as refusal:
        return {
            "success": False,
            "allowed": False,
            "decision": "refused",
            "status": "rejected",
            "reason": refusal.reason,
            **refusal.detail,
        }


def get_capabilities() -> Dict:
    """
    What AEGIS can pay for — used by the UI and by the no-match response.
    """

    return {
        "providers": catalog.KNOWN_PROVIDERS,
        "categories": catalog.describe_capabilities(),
    }
