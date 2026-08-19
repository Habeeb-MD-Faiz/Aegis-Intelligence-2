# Operating AEGIS

A guide for the person watching the dashboard — not the person editing the code.

## What AEGIS does for you

Your AI agents need to buy things: market data, flight searches, image
generation, translation. You want them to get on with it without asking
permission for every $2 API call — and you want to be certain they can't spend
$5,000 on a service nobody approved.

AEGIS sits in the middle. Agents can't pay anyone directly; they ask AEGIS, and
AEGIS decides. Every decision is explained and permanently recorded.

## The three outcomes

Every request ends in one of three states. This is the heart of it — AEGIS
isn't an on/off switch.

| Outcome | What happened | You do |
|---|---|---|
| 🟢 **Approved** | Within every rule. Paid automatically. | Nothing |
| 🟡 **Pending** | Legitimate but above the autonomous limit. | Approve or reject it |
| 🔴 **Rejected** | Broke a rule — unknown provider, over budget, too frequent. | Nothing; review if unexpected |

The middle row is the point. Blocking everything is easy and useless; approving
everything is what you're trying to avoid.

## Reading a decision

Open any request and you'll see the rules that ran, each with a verdict:

```
✓ Request Frequency Limit   Within frequency limit (3 of 25 in the last 24h).
✓ Provider Allow List       'Bloomberg' is an allowed provider.
✓ Daily Budget              Within daily budget ($1,240.00 of $5,000.00).
✗ Amount Threshold          $150.00 exceeds the autonomous limit of $100.00;
                            human approval required.
```

Read it top to bottom. Checks run in order and stop at the first hard failure,
so the last line is always the one that decided the outcome.

**A decision nobody can explain isn't governance.** If a request surprises you,
this list tells you exactly which rule fired and what the numbers were at the
time.

## Approving a pending request

1. Open **Approval Center** or **Payment Requests**
2. Find the request with the amber *pending* badge
3. Check the reason and the amount
4. **Approve** or **Reject**

On approval, AEGIS creates the payment and generates the transaction ID — the
interface never invents one. The decision is written to the ledger, stamped
with **User** rather than **Guardrails**, so the audit trail distinguishes what
a human decided from what policy decided automatically.

Deciding twice is safe. A request that's already final stays that way and
doesn't create a second payment.

## Risk, and where it comes from

Alongside the pass/fail rules, every request gets a behavioural risk level
computed from that agent's own history:

| Signal | Meaning |
|---|---|
| First payment to a provider | this agent has never paid them before |
| New category | first time this agent has spent here |
| Spend deviation | far above this agent's normal amount |
| Velocity | a burst of requests in a few minutes |
| Recent refusals | this agent has just been blocked repeatedly |

Each shows its own reason, so "medium risk" is never unexplained. Risk can
raise a level but never lower it — a blocked payment is high risk however
ordinary it looked.

There is no AI in this scoring, deliberately. The same request scores the same
way twice, and you can always see which signal fired.

## The five guardrails

Found under **Guardrails**. Each can be armed or disarmed independently.

| Guardrail | Controls |
|---|---|
| **Provider Allow List** | Which providers agents may use at all |
| **Autonomous Approval Limit** | Ceiling for automatic approval (default $100) |
| **Human Review Threshold** | Ceiling for escalation — above it, rejected outright (default $1,000) |
| **Daily Spending Budget** | Total across all agents per day (default $5,000) |
| **Request Frequency Limit** | Requests allowed in a rolling window (default 25 / 24h) |

Changing one takes effect on the very next request — no restart, no redeploy.

> **Disarming a guardrail needs an operator credential.** Agents are refused
> here by construction, so a compromised agent can't turn off the rules that
> govern it. Where `AEGIS_OPERATOR_TOKEN` isn't configured this page is open to
> anyone who can reach it; check **Settings** or `GET /config` to see which
> state your deployment is in.

## Policy that proposes its own changes

**Policy Builder** reads the decisions AEGIS has actually made and suggests
amendments:

> *"You've manually approved Skyscanner above the autonomous limit 3 times in
> the last week. Consider raising the limit to $150."*
> Confidence 78 · Evidence 3 · Recommendation: relax

Every suggestion shows what it's based on and how many times it saw the pattern.

**Nothing applies itself.** A suggestion is a recommendation until a human
presses apply, and applying it is an operator action. That's deliberate: a
governance system that rewrites its own rules unsupervised is exactly the
failure mode this exists to prevent.

Suggestions need `GROQ_API_KEY` configured. Without it you'll see an explanatory
message and everything else keeps working.

## The audit ledger

**Blockchain Command Center** shows every final decision as a linked block:
what was requested, which provider, how much, what was decided, why, by whom,
and when.

Each block carries a hash of the one before it, so altering any past record
breaks every hash after it. **Verify chain** re-derives all of them and names
the first tampered block.

If on-chain anchoring is configured, the chain head is periodically written to
Base Sepolia with an explorer link — so rewriting history locally would also
require altering a record you don't control. The page states plainly whether
anchoring is on; when it's off, the ledger is still tamper-evident locally.

## What's real and what isn't

Worth knowing before you show this to anyone.

| Component | Status |
|---|---|
| Policy engine and decisions | Real |
| Human approval flow | Real |
| Credential custody | Real |
| Audit ledger and verification | Real |
| Behavioural risk scoring | Real |
| On-chain anchoring | Built and tested offline; the live broadcast needs a funded key — run `anchor_preflight.py` |
| x402 payment lifecycle | **Simulated** — real state machine, stubbed settlement |
| Money movement | **None.** No funds ever move |
| Analytics | Real — reads live decisions |
| Incidents / Audit Logs / Approval Center | **Fixture data**, not live |

Settled payments are labelled `settlement_mode: "simulated"` in the API for
exactly this reason.

## Common questions

**An agent got rejected and I don't know why.**
Open the request and read the checks. The last failing line decided it.

**Can I let one agent spend more than another?**
Not yet — limits are global. Per-agent policy is a natural next step; requests
already carry an `agentId`.

**What if AEGIS goes down?**
Nothing spends. The guard fails closed by design — no approvals happen while it
can't evaluate.

**An agent tried to pay a company I've never heard of.**
It was refused before policy even ran. AEGIS only pays providers in its
catalog, so an agent can't be talked into paying an arbitrary destination —
which is the main way a prompt-injection attack would try to move money.

**Where did my transactions go after a restart?**
Free hosting tiers use ephemeral disks. See the deployment notes in
[SETUP.md](SETUP.md).
