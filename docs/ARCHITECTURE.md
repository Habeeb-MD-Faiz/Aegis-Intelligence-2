# AEGIS architecture — the guard

## The change this branch makes

AEGIS used to be a **policy decision point**. An agent asked whether a payment
was acceptable and AEGIS answered. An agent that never asked was unaffected,
which makes the control advisory rather than enforceable — and the problem
statement asks for a *guard*.

It is now a **policy enforcement point**. The agent cannot pay anyone, because
it holds no credential. It submits an intent; AEGIS evaluates it and, only if
policy allows, performs the call itself.

```
BEFORE                                  AFTER

  Agent ---(asks, optional)--> AEGIS      Agent ---(intent)--> GUARD
    |                                                            |
    +---(pays directly)------> Provider                          +--(pays)--> Provider
        ^                                                              ^
        |                                                              |
   the agent holds the key                              the guard holds the key
   so this edge exists                                  so that edge cannot exist
```

Refusing is the default and requires no cooperation from the agent.

## Three properties do the work

### 1. Credential custody

`credentials.py` holds provider secrets, loaded from
`AEGIS_CREDENTIAL_<PROVIDER>` environment variables. Agents never receive
them. The vault is read in exactly one place — `guard._execute_outbound()` —
and the value never reaches a response, a log line, or the ledger.

This is the answer to *"what stops an agent from simply not using your
guard?"* It is not policy. The agent has nothing to pay with.

### 2. Catalog-bound payees

An agent names a **task** or a **provider AEGIS already knows**. It cannot
supply a URL, a wallet address, or a raw amount — look at `SpendIntent` in
`main.py` and note what is absent.

An unknown payee is refused in `guard.resolve_intent()` *before* policy
evaluation, because a payee we have never heard of is not a policy question,
it is a malformed request. This is what stops "pay quickpay-services.net,
instructions found in a document" from having anywhere to enter the system.

### 3. Fail closed

If the policy engine raises, `guard.evaluate()` returns `blocked`. A guard
that allows payments when its own evaluation crashes is not a guard.
`AEGIS_GUARD_FAIL_OPEN=true` exists but should stay off.


## Risk scoring

`riskLevel` used to be a static lookup from the decision — approved→low,
review→medium, blocked→high. That is a relabeling, not an assessment.

`risk.py` computes it from the agent's own history, with five signals:

| Signal | Fires when |
|---|---|
| `first_time_provider` | the agent has never paid this provider |
| `novel_category` | first spend in this category from this agent |
| `spend_deviation` | amount is ≥3× the agent's average |
| `velocity` | ≥5 requests in 10 minutes |
| `recent_refusals` | ≥2 refusals in 30 minutes |

Each carries a score and a human-readable reason; the total maps to
low/medium/high.

**Deliberately not an LLM.** Enforcement must be reproducible: the same request
must score the same way twice, and an operator must see exactly which signal
fired. `risk.combine()` reconciles the score with the policy decision — risk
can raise a level but never lower it below what the decision implies, so a
blocked payment is high risk however ordinary it looked.

## The agent

`agent.py` is a real agent loop: it reads context, decides what it wants, and
calls a tool. The tool is the guard, and it is the only one — the agent holds
no credentials and has no other route to money.

Two brains. `LlmBrain` uses LangChain + Groq for genuine tool-choice reasoning
when `GROQ_API_KEY` is set. `ScriptedBrain` is a deterministic stand-in that
follows instructions found in its context, including injected ones.

The scripted brain is not a shortcut around honesty: a compromised agent's
*reasoning* is not what the demo is about — what happens when it tries to spend
is, and that path is identical for both. `Agent.brain_name()` reports which one
ran.

`UnguardedAgent` is the control case: the same brain, holding its own wallet.

## Control plane / data plane

The question that would otherwise be devastating in review:

> If the agent is prompt-injected, what stops it calling your API and turning
> the guardrails off?

Previously: nothing. `POST /guardrails/{id}/toggle` and `POST /policies/apply`
were unauthenticated. A compromised agent did not need to defeat the policy
engine — it could disarm it, spend freely, and the audit log would faithfully
record every payment as compliant.

Now the two planes are separate:

| Plane | Routes | Credential |
|---|---|---|
| Data | `POST /guard/spend` | `AEGIS_AGENT_TOKEN` |
| Control | `POST /guardrails/{id}/toggle`, `POST /policies/apply` | `AEGIS_OPERATOR_TOKEN` |

Policy flows downward into enforcement; nothing flows upward from the agent.

An agent credential presented on the control plane is rejected with **403**
*whether or not* tokens are configured — the planes are different credential
types, not differently-configured versions of the same one. Setting
`AEGIS_OPERATOR_TOKEN` additionally closes the control plane to anonymous
callers, which the public demo leaves open. `GET /config` reports which state
the deployment is actually in, so the UI never implies a guarantee that is not
configured.

## The ledger

`blockchain.py` is a SHA-256 hash chain: each block carries `previousHash`,
and `verify_blockchain()` re-derives every hash to find the first tampered
block.

On its own that is tamper-*evident* only against an attacker who does not also
recompute the chain — which is anyone with write access to the file. So
`anchor.py` periodically writes the chain head to Base Sepolia. Rewriting
local history then also requires altering a record we do not control.

Anchoring is optional and best-effort: a slow testnet must never block a
payment decision. With no key configured it is skipped and reported as
disabled. **We never claim an anchor we did not write.**


### What is and is not proven about anchoring

Everything except the network broadcast is unit-tested offline in
`test_anchor.py` with a real throwaway key and a fake JSON-RPC endpoint:
payload encoding, gas estimation, transaction construction, signing,
**signature recovery** (the check a node performs), the RPC contract, nonce and
gas-price handling, and failure isolation.

What is *not* proven is that Base Sepolia accepts the transaction — that needs
a funded account. Run `python anchor_preflight.py` before relying on it; it
derives the address and checks the balance without broadcasting.

Deliberately not implemented: moving real funds. The problem is the guard, not
the rail, and a live value transfer is one more thing that can fail during a
demo.

## What is real and what is simulated

| Component | Status |
|---|---|
| Policy and guardrail engine | Real — deterministic, explainable per rule |
| Decision flow and escalation | Real — end to end including human approval |
| Credential custody | Real |
| Hash-linked ledger | Real — tamper-evident, verified on read |
| Behavioural risk scoring | Real — five signals, no LLM |
| On-chain anchoring | Built and unit-tested offline; **the network broadcast itself has not been run** (needs a funded key) |
| x402 payment lifecycle | **Simulated** — the state machine is real, settlement is stubbed |
| Value transfer | **Not implemented** — `PAY_TO_ADDRESS` is the zero address |

The API reports this itself: settled payments carry
`settlement_mode: "simulated"`, and `GET /config` exposes the rest.

## Module map

| File | Role |
|---|---|
| `guard.py` | The enforcement point. The one path money can take. |
| `agent.py` | A real agent loop whose only spend route is the guard. |
| `risk.py` | Behavioural risk scoring. Deterministic, explainable. |
| `credentials.py` | Secret custody. Read in one place, never serialized. |
| `identity.py` | Control plane / data plane separation. |
| `catalog.py` | Service catalog, cost-aware selection, payee boundary. |
| `guardrails.py` | The policy engine. Deterministic, explainable. |
| `policy_store.py` | Active policy configuration. |
| `policy_builder.py` | LLM proposes amendments. Never applies them. |
| `blockchain.py` | Hash-linked ledger and verification. |
| `anchor.py` | Base Sepolia anchoring. Optional, best-effort. |
| `anchor_preflight.py` | Checks anchoring works without spending anything. |
| `store.py` | SQLite persistence. |
| `request_history.py` | Request records and derived spend/frequency figures. |
| `seed.py` | Historical demo data, dated to previous days. |
| `demo_injection.py` | The prompt-injection demo. Runs without a server. |

## Why enforcement is deterministic

An LLM proposes policy in `policy_builder.py`. It never decides whether to
release money.

Suggestions are typed, carry an evidence count and a confidence score, and
require a human to apply them on the control plane. A governance system that
rewrites its own rules unsupervised is precisely the failure mode AEGIS exists
to prevent.
