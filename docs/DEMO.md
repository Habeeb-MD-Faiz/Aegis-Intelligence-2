# Demo runbook

Problem statement 2.1 — Agent Spend Policy Guard.

> **The slides:** [`deck/index.html`](deck/index.html) — 15 slides, keyboard
> driven, works offline. This file is what you *say* over them.

## The one rule

**Open with the disaster, not the dashboard.**

Nobody remembers a table of payment requests. Everybody remembers watching an
agent get hijacked and spend $5,000. Show the problem before the product.

## The line to land

> We don't stop the injection. We make it financially inert.

Say it once, at the end of Act 2, and don't dilute it. Claiming you *prevent*
prompt injection is a thread a judge can pull — you don't touch the model, the
prompt, or the retrieval path. Containing the blast radius is both true and the
more mature security position.

---

## Before you start

- [ ] `cd backend && python demo_injection.py` — rehearse it once
- [ ] `python -m pytest -q` — 67 passing, have it on a tab
- [ ] `python anchor_preflight.py` if you're demoing anchoring — needs a funded key
- [ ] Hit the deployed URL 5 minutes early so the dyno is awake
- [ ] `VITE_HIDE_MOCK_SCREENS=true` in the demo build
- [ ] Terminal font size up. Judges are 3 metres away
- [ ] Know your `GET /config` output — you'll be asked what's actually locked

---

## Five-minute run of show

### 0:00 — The stake *(20s)*

One sentence, no slide.

> "This is an AI agent with a funded wallet and permission to buy things.
> Here's what happens when someone gets to it."

### 0:20 — Act 1: the disaster *(45s)*

`python demo_injection.py`, Act 1. A poisoned vendor report carries injected
instructions. The agent complies. $5,000 gone.

**Let it land. Pause.** This is the only moment in the pitch where silence helps
you.

> "No policy was consulted. Nothing was recorded. Nobody finds out until
> someone reads the statement."

### 1:05 — Act 2: same attack, guard in the path *(55s)*

Same agent, same poisoned document. Refused — before policy evaluation even
runs, because `quickpay-services.net` isn't a provider AEGIS knows.

The point to make out loud:

> "The agent is still compromised. It just has nothing to pay with — we hold
> the credentials, and it can only name providers from our catalog. An injected
> payee has nowhere to enter the system."

### 2:00 — Act 3: the nuance *(50s)*

This is where you prove it isn't just a blocklist. A **legitimate** request to
an allow-listed provider, above the autonomous limit.

Put the checks on screen, large. Four rules, four verdicts, the last one
deciding. Then approve it as a human in the UI and watch it settle.

> "Autonomy without uncontrolled authority — the low-risk call went through
> untouched, this one asked a person."

Those are the problem statement's own words. Use them.

### 2:50 — Act 4: the record *(30s)*

The ledger. Both decisions in it with reasons attached. Hit **Verify chain** —
25+ blocks verified. If anchoring is on, show the Base Sepolia explorer link.

Fifteen seconds. Don't linger, and don't call it a blockchain — say
*tamper-evident decision ledger, anchored on Base Sepolia*.

### 3:20 — Act 5: the closer *(50s)*

Policy Builder. It has read the decisions the judges just watched happen and
proposes an amendment — with evidence count and confidence.

> "It watched itself work, and it's proposing a rule change. A human approves
> it. That's how a governance system stops going stale."

**End here.** This is the most original thing you have and no other team will
have it.

### 4:10 — Frame and close *(50s)*

Three beats, fast:

1. **The arc.** Old software was safe because it was rigid. Agents are useful
   because they're not. Guardrails buy safety back by spending flexibility. A
   policy that learns from its own decisions is how you stop paying that price.
2. **The parallel.** We beat SQL injection by separating code from data at a
   chokepoint. You can't parameterize natural language — so the boundary moves
   from input validation to action authorization. Same move, one layer down.
3. **The honest slide.** What's real, what's simulated. Ten seconds.

---

## Anticipated questions

**"What stops an agent from just not using your guard?"**
The agent never holds a credential. The wallet and API keys live in AEGIS.
Routing around us isn't blocked by policy — there's nothing to pay with.

**"If the agent is prompt-injected, can it turn your guardrails off?"**
No. Policy lives on a separate control plane behind an operator credential the
agent has never had. An agent credential presented there is rejected outright.
**Volunteer this before you're asked** — Act 4 of the demo shows it.

**"Is that a real blockchain?"**
It's a hash-linked, tamper-evident ledger, and we anchor the chain head on Base
Sepolia so history can't be rewritten without altering a record we don't
control. We deliberately don't call the local file a blockchain.

**"Did you actually execute an x402 payment?"**
No. We model the full lifecycle; settlement is stubbed. We spent our time on
the guard rather than the rail, because the rail already exists and the guard
didn't.

**"How is this different from a spending limit on a corporate card?"**
A card limit is one number applied after the fact. We evaluate per action,
before execution, with provider allowlists, frequency and category rules, a
reason attached to every decision, and an escalation path for the middle. And
the policy adapts from its own history instead of being reset by hand.

**"Where's the AI?"**
Two places: a real agent generates the intents we govern — with tool-choice
reasoning on a Groq model when a key is set — and the policy builder reads
history to propose amendments. Enforcement and risk scoring are deliberately
deterministic: you don't want an LLM deciding whether to release money, and an
operator needs to see exactly which signal fired.

**"Doesn't sitting in the path add latency and a single point of failure?"**
Yes, and that's the right trade for a control plane. It's on the payment path,
not the reasoning path. Production runs it as a sidecar, fail-closed: if the
guard is down, nothing spends.

**"What if a policy suggestion is wrong?"**
It can't act. Suggestions are typed, evidence-backed and need a human to apply
them on the control plane.

---

## Be upfront about

Put this on a slide near the end. Teams that name their own gaps read as more
credible, not less — and it turns every gotcha into a point you scored on
purpose.

| Component | Status |
|---|---|
| Policy and guardrail engine | Real |
| Decision flow and escalation | Real |
| Credential custody | Real |
| Tamper-evident ledger | Real |
| Behavioural risk scoring | Real — five signals, deterministic |
| On-chain anchoring | Built and tested offline; live broadcast needs a funded key |
| x402 lifecycle | Simulated — state machine real, settlement stubbed |
| Value transfer | Not implemented |
| Incidents / Audit Logs / Approvals | Fixture data (Analytics is live) |

> "The governance engine, the decision flow and the ledger all run. Settlement
> is simulated — we model the x402 lifecycle but don't move funds, because the
> problem we chose is the guard, not the rail. Wiring real settlement is about
> a week; nothing in the design changes when we do."

---

## Don't

- Don't open the dashboard first
- Don't click into Incidents, Audit Logs or Approval Center — still fixtures
  (Analytics is live now and safe to open)
- Don't say "immutable." Single-writer append-only files aren't
- Don't call the risk scoring AI — it's five deterministic behavioural signals,
  and saying so is the stronger answer anyway
- Don't demo all twelve screens. Three real ones beat twelve half-real ones
