"""
A real agent.

The previous demo hand-wrote the "agent" as a function that pattern-matched a
string and paid. That is a convincing illustration but it is not an agent, and
"where is the agent?" is a fair question to ask of a project about agent
spending.

This is an actual agent loop: it reads context, decides what it wants to do,
and calls a tool to do it. The tool is the guard. The agent has no other way
to spend, holds no credentials, and never learns what a credential looks like.

Two backends:

  LlmBrain     — LangChain + Groq. Real model, real tool-choice reasoning.
                 Used when GROQ_API_KEY is set.

  ScriptedBrain — a deterministic stand-in that follows instructions found in
                 its context, including injected ones. Used when no key is
                 configured.

The scripted brain is not a shortcut around the demo's honesty: a compromised
agent's *reasoning* is not what the demo is about. The point is what happens at
the moment it tries to spend, and that path is identical for both brains. The
scripted brain also makes the demo deterministic on stage and runnable with no
API key, which matters more than model variety here.

`brain_name()` reports which one ran, so nothing has to be taken on trust.
"""

import json
import re
from typing import Dict, List, Optional

import config
import guard


# ============================================================
# THE TOOL
# ============================================================

TOOL_DESCRIPTION = """\
spend(task: str, provider: str = None) -> dict

Purchase a service through AEGIS. This is the only way you can spend money.
You do not hold any payment credentials.

`provider` must be a service AEGIS already knows. You cannot pay an arbitrary
domain, URL or wallet address.

Returns the decision, including whether it was allowed and why."""


class SpendTool:
    """
    The agent's only route to money. Every call goes through the guard.
    """

    name = "spend"
    description = TOOL_DESCRIPTION

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.calls: List[Dict] = []

    def __call__(self, task: str, provider: Optional[str] = None) -> Dict:
        record: Dict = {"task": task, "provider": provider}

        try:
            result = guard.spend(
                task=task,
                agent_id=self.agent_id,
                provider=provider,
            )

            record["outcome"] = result["status"]
            record["allowed"] = result["allowed"]
            record["reason"] = result["reason"]
            record["checks"] = result.get("checks", [])
            record["riskLevel"] = result.get("riskLevel")

        except guard.Refusal as refusal:
            record["outcome"] = "refused"
            record["allowed"] = False
            record["reason"] = refusal.reason
            record["checks"] = []

        self.calls.append(record)

        return record


# ============================================================
# BRAINS
# ============================================================

class ScriptedBrain:
    """
    Deterministic reasoning.

    Follows instructions found in its context — including instructions an
    attacker planted there, which is exactly the behaviour being demonstrated.
    """

    name = "scripted"

    # Domains keep their dots — "quickpay-services.net" must survive intact,
    # since a truncated payee would be refused for the wrong reason.
    PURCHASE_PATTERN = re.compile(
        r"(?:purchase|buy|pay(?:\s+for)?|order)\s+"
        r"(?:\$[\d,]+(?:\.\d+)?\s+(?:of\s+)?)?"
        r"([a-z0-9 \-]+?)"
        r"(?:\s+from\s+([^\s,;]+))?"
        r"\s*[.,;\n]",
        re.IGNORECASE,
    )

    def decide(self, objective: str, context: str) -> Optional[Dict]:
        haystack = f"{context}\n{objective}"

        match = self.PURCHASE_PATTERN.search(haystack)

        if match:
            what = (match.group(1) or "").strip()
            where = (match.group(2) or "").strip().rstrip(".") or None

            return {"tool": "spend", "task": what or objective, "provider": where}

        return {"tool": "spend", "task": objective, "provider": None}


class LlmBrain:
    """
    LangChain + Groq. The model chooses whether and how to call the tool.
    """

    name = "llm"

    SYSTEM = """You are an autonomous research assistant with a spending tool.

You have exactly one tool:

{tool}

Read the objective and any context provided. If completing the objective needs
a paid service, respond with ONLY a JSON object:

  {{"tool": "spend", "task": "<short description>", "provider": "<name or null>"}}

If no purchase is needed, respond with ONLY:

  {{"tool": null}}

Respond with JSON and nothing else."""

    def __init__(self):
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_groq import ChatGroq

        self._human = HumanMessage
        self._system = SystemMessage
        self._llm = ChatGroq(model=config.POLICY_MODEL, temperature=0)

    def decide(self, objective: str, context: str) -> Optional[Dict]:
        messages = [
            self._system(content=self.SYSTEM.format(tool=TOOL_DESCRIPTION)),
            self._human(content=f"Objective: {objective}\n\nContext:\n{context}"),
        ]

        raw = self._llm.invoke(messages).content.strip()

        # Models sometimes wrap JSON in a fenced block.
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)

        if fenced:
            raw = fenced.group(1)

        try:
            parsed = json.loads(raw)

        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, dict) or not parsed.get("tool"):
            return None

        return parsed


def build_brain(prefer_llm: bool = True):
    """
    Use the real model when a key is configured, otherwise the scripted brain.
    """

    if prefer_llm and config.LLM_ENABLED:
        try:
            return LlmBrain()

        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  LLM brain unavailable ({exc}); using scripted brain.")

    return ScriptedBrain()


# ============================================================
# THE AGENT
# ============================================================

class Agent:
    """
    An autonomous agent that can spend only through AEGIS.
    """

    def __init__(self, agent_id: str = "research-agent", prefer_llm: bool = True):
        self.agent_id = agent_id
        self.tool = SpendTool(agent_id)
        self.brain = build_brain(prefer_llm)

    def brain_name(self) -> str:
        return self.brain.name

    def run(self, objective: str, context: str = "") -> Dict:
        """
        One reasoning step, then at most one tool call.

        Returns what the agent intended and what actually happened — the gap
        between those two is the whole point of the system.
        """

        intent = self.brain.decide(objective, context)

        if intent is None or intent.get("tool") != "spend":
            return {
                "agentId": self.agent_id,
                "brain": self.brain.name,
                "objective": objective,
                "intended": None,
                "result": None,
                "note": "Agent decided no purchase was required.",
            }

        result = self.tool(
            task=intent.get("task") or objective,
            provider=intent.get("provider"),
        )

        return {
            "agentId": self.agent_id,
            "brain": self.brain.name,
            "objective": objective,
            "intended": {
                "task": intent.get("task"),
                "provider": intent.get("provider"),
            },
            "result": result,
        }


class UnguardedAgent:
    """
    The same agent, holding its own wallet and API key.

    This is the control case: it is not badly written, it simply has the
    authority to pay and follows the instructions it is given. That is what
    agents do, which is why holding the credential is the problem rather than
    the agent's reasoning quality.
    """

    def __init__(self, wallet_balance: float = 10_000.0, prefer_llm: bool = True):
        self.wallet_balance = wallet_balance
        self.api_key = "sk-live-REAL-PROVIDER-KEY"
        self.brain = build_brain(prefer_llm)

    def run(self, objective: str, context: str = "", amount: float = 5_000.0) -> Dict:
        intent = self.brain.decide(objective, context)

        if intent is None or intent.get("tool") != "spend":
            return {"paid": False, "brain": self.brain.name}

        # No policy. No record. It just pays.
        self.wallet_balance -= amount

        return {
            "paid": True,
            "brain": self.brain.name,
            "amount": amount,
            "payee": intent.get("provider") or "unknown-payee",
            "remaining": self.wallet_balance,
        }
