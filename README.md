🛡️ AEGIS — AI Agent Payment Governance

A policy **enforcement point** for autonomous AI-agent payments.

AEGIS sits between AI agents and the services they pay for. Agents hold no
credentials — they submit an intent, and AEGIS evaluates it against
configurable policy and, only if allowed, makes the paid call itself.

The distinction matters. A layer agents *report to* is advisory: an agent that
never asks is unaffected. A layer that *holds the only credential* is
enforceable, and refusing requires no cooperation from the agent.

    We don't stop prompt injection. We make it financially inert.

See `docs/ARCHITECTURE.md` for how that works, and run the demo below to watch
it happen.

## ⚡ The 60-second demo

    cd backend
    pip install -r requirements.txt
    python demo_injection.py

Runs a real agent through the same prompt-injection attack four times —
holding its own wallet, behind AEGIS, against a legitimate provider, and
finally attacking the guard itself. No server and no API key needed.

## 🧪 Tests

    cd backend
    python -m pytest test_guard.py -v

67 tests: the guard's security properties, the agent, behavioural risk
scoring, the live credential-injected call path, on-chain anchoring
(signing and signature recovery included), and every bug this work fixed.

## 🎤 The pitch deck

Open [`docs/deck/index.html`](docs/deck/index.html) in any browser and press
<kbd>F11</kbd>. Fifteen slides, keyboard driven (<kbd>←</kbd> <kbd>→</kbd>),
no build step and no network — it works on conference wifi because it never
touches it.

What to say over each slide is in [docs/DEMO.md](docs/DEMO.md).


🚨 Problem

As AI agents become increasingly autonomous, they can also initiate financial transactions with limited human intervention. This introduces risks such as:

Unauthorized spending

Excessive or budget-breaking payments

Unintended transactions

Repeated or duplicate transactions

Transactions with untrusted providers

Limited visibility into agent-driven financial activity

💡 Solution

Agents hold no payment credentials. They submit an intent; AEGIS evaluates it and,
only if policy allows, makes the paid call itself using a secret the agent has
never seen.

```
AI Agent  (holds no credentials)
    ↓  submits an intent — a task, or a provider from the catalog
AEGIS GUARD
    ↓  frequency → provider allow list → daily budget → amount
Policy engine + behavioural risk scoring
    ↓
APPROVE  ·  ESCALATE TO HUMAN  ·  BLOCK
    ↓  (approved only)
Credential injection → paid call → x402 lifecycle
    ↓
Tamper-evident decision ledger  →  optional Base Sepolia anchor
```

Refusing is the default and needs no cooperation from the agent — it has
nothing to pay with.

✨ Key Features

🔐 **Credential custody** — provider secrets live in the guard, read in exactly one
place, and never reach a response, a log line, or the ledger.

🚧 **Catalog-bound payees** — an agent names a task or a known provider. It cannot
supply a URL, a wallet address, or an amount, so injected payment instructions
have nowhere to enter.

🛡️ **Five guardrails** — provider allow list, autonomous approval limit, human
review threshold, daily budget, request frequency. Each can be armed or disarmed
independently.

⚡ **Three-way decisions** — approve, escalate to a human, or block. Every rule
reports its own verdict and the numbers it saw.

📊 **Behavioural risk scoring** — five deterministic signals from the agent's own
history: first-time provider, novel category, spend deviation, velocity, recent
refusals. No LLM in the scoring path.

🔀 **Control plane / data plane split** — policy changes need an operator
credential. An agent credential is rejected there by construction, so a
compromised agent cannot disarm its own guard.

🤖 **Policy Builder** — reads the system's own decision history and proposes
amendments with evidence counts and confidence. Nothing applies itself.

⛓️ **Tamper-evident ledger** — hash-linked decision records, verified on read,
optionally anchored on Base Sepolia.

👤 **Human-in-the-loop approvals** — idempotent; deciding twice never creates a
second payment.

📸 Project Screenshots

The repository includes screenshots of the main AEGIS interfaces.

⛓️ Blockchain Command Center

![Blockchain Command Center](screenshots/blockchain.png)

🎛️ Command Center

![Command Center](screenshots/command_center.png)

🛡️ Guardrails

![Guardrails](screenshots/guardrails.png)

📋 Policy Builder

![Policy Builder](screenshots/policy%20builder.png)

💳 Payment Requests

![Payment Requests](screenshots/requests.png)

🔎 Transaction Details

![Transaction Details](screenshots/transaction.png)

👤 Human Approval

![Human Approval](screenshots/user_approval.png)

🏗️ Architecture

```
        ┌──────────────────────┐
        │      AI AGENT        │   holds no credentials
        └──────────┬───────────┘
                   │  spend intent  (task or known provider)
                   ↓
   ╔═══════════════════════════════════╗
   ║           AEGIS GUARD             ║   the only path money can take
   ║                                   ║
   ║  resolve intent → catalog only    ║
   ║  policy engine  → 5 guardrails    ║
   ║  risk scoring   → 5 signals       ║
   ║  fail closed    → errors = no     ║
   ╚═══════════════┬═══════════════════╝
                   │
     ┌─────────────┼─────────────┐
     ↓             ↓             ↓
  APPROVE      ESCALATE        BLOCK
     │             │             │
     │             ↓             │
     │      human decision       │
     │        (operator)         │
     └──────┬──────┘             │
            ↓                    │
   credential injection          │
   paid call + x402 lifecycle    │
            │                    │
            └────────┬───────────┘
                     ↓
        tamper-evident ledger  →  Base Sepolia anchor (optional)


   CONTROL PLANE  ── operator credential ──▶  policy store
        │                                          │ reads
        └──────────────  agents cannot reach  ─────┘
```

🧰 Technology Stack

Layer

Technology

Frontend

React, TypeScript, Vite, Tailwind CSS

Backend

Python, FastAPI

AI / Agent Components

LangChain + Groq — used for policy suggestions only. Enforcement is deterministic; an LLM never decides whether to release money.

Governance

Custom Policy Engine + Guardrail Engine

Payments

x402-style payment lifecycle

Blockchain

Hash-linked decision ledger, optionally anchored on Base Sepolia. Settlement is simulated — no funds move.

Database

SQLite — implemented; requests, payments and decisions persist across restarts

APIs

REST

Version Control

Git + GitHub

Deployment

Render

📁 Project Structure

```
Aegis/
├── backend/
│   ├── guard.py              # THE ENFORCEMENT POINT — one path money can take
│   ├── agent.py              # a real agent whose only spend route is the guard
│   ├── risk.py               # behavioural risk scoring (no LLM)
│   ├── credentials.py        # secret custody; agents never hold a key
│   ├── identity.py           # control plane / data plane separation
│   ├── catalog.py            # service catalog + payee boundary
│   ├── guardrails.py         # the policy engine (deterministic)
│   ├── policy_store.py       # active policy configuration
│   ├── policy_builder.py     # LLM proposes amendments; never applies them
│   ├── blockchain.py         # hash-linked decision ledger
│   ├── anchor.py             # Base Sepolia anchoring (optional)
│   ├── anchor_preflight.py   # verify anchoring works, spend nothing
│   ├── store.py              # SQLite persistence
│   ├── request_history.py    # records + derived spend/frequency
│   ├── seed.py               # historical demo data
│   ├── config.py             # env-driven configuration
│   ├── selector.py           # legacy entry point -> guard
│   ├── main.py               # FastAPI routes
│   ├── demo_injection.py     # ▶ the demo — runs without a server
│   ├── test_guard.py / test_agent.py / test_anchor.py   # 67 tests
│   ├── api_catalog.json / keyword_map.json / blockchain.json
│   ├── requirements.txt / .env.example
│   └── x402/                 # payment lifecycle (simulated settlement)
├── frontend/
│   ├── src/config.ts         # single source for API URL + credentials
│   └── src/…                 # pages, services, components
├── docs/
│   ├── ARCHITECTURE.md       # how the guard works
│   ├── API.md                # endpoint reference
│   ├── SETUP.md              # install, config, deployment
│   ├── OPERATING.md          # using the dashboard
│   ├── DEMO.md               # demo runbook — what you say
│   └── deck/index.html       # ▶ the pitch deck — what you show
└── screenshots/
```

## 📚 Documentation

| Doc | For |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | How enforcement works, and why it's a guard rather than a dashboard |
| [API.md](docs/API.md) | Every endpoint, auth, request/response examples |
| [SETUP.md](docs/SETUP.md) | Install, configure, deploy, troubleshoot |
| [OPERATING.md](docs/OPERATING.md) | Operator guide — reading decisions, approving requests, guardrails |
| [DEMO.md](docs/DEMO.md) | Demo runbook and anticipated questions |
| [deck/index.html](docs/deck/index.html) | **The pitch deck** — 15 slides, keyboard driven, opens offline in any browser |

## 🤖 Working on this with a coding agent

[`AGENTS.md`](AGENTS.md) is the context file: what AEGIS is, the invariants that
must not be broken, the module map, how to run and test, current real-vs-simulated
state, and what to do next. Clone the repo, open any agent, and it has the
full picture.

`CLAUDE.md` is a byte-identical copy for Claude Code, and Cursor, Copilot and
Windsurf read pointer files that defer to `AGENTS.md` — so there is exactly one
place to edit. `scripts/sync_agent_docs.py` keeps them identical and CI fails if
they drift. See [scripts/README.md](scripts/README.md).

💳 x402 Integration

x402 is an HTTP-native approach to programmatic payments built around the 402 Payment Required mechanism.

AEGIS uses an x402-style payment lifecycle within its governance and transaction workflow:

Payment Required → Authorized → Verified → Settling → Settled

🔗 The guard (formerly "planned x402 gateway")

Built. AEGIS sits between agents and providers rather than beside them:

```
AI Agent  (holds no credentials)
   ↓  submits an intent
AEGIS GUARD
   ↓  frequency → provider → budget → amount
Policy + Guardrails
   ↓  approve · escalate · block
Credential injection  (the agent never sees the key)
   ↓
Payment lifecycle → Settlement (simulated)
   ↓
Tamper-evident ledger → optional Base Sepolia anchor
```

The agent cannot pay a provider directly, so the guard cannot be bypassed by an
agent that simply declines to ask. See
[ARCHITECTURE.md](docs/ARCHITECTURE.md).

🗄️ Persistence

Implemented. SQLite (`store.py`) persists payment requests, transactions,
payment records and decisions across restarts. The ledger lives in
`blockchain.json` and is verified on every read.

Note: free hosting tiers use ephemeral disks, so a recycled instance still
resets state — see [SETUP.md](docs/SETUP.md).

🔄 Governance Scenarios

Scenario

Expected Result

Low-risk request within policy

🟢 Automatic Approval

Legitimate request exceeding autonomous threshold

🟡 Human Approval

Request violating a configured guardrail

🔴 Rejection

This demonstrates that AEGIS does not simply allow or block all autonomous payments — it applies context-aware governance.

🌐 API Catalog

AEGIS can model payment requests for services across categories such as:

Financial research

Travel

Maps

Email

Documents

Image generation

Video generation

Speech

Translation

Weather

Web search

Code

Payments

The API catalog contains providers, estimated request costs, categories, and descriptions used by the payment-selection and governance workflow.

☁️ Deployment

Frontend and backend deploy as two services on Render. Root directories,
build and start commands, the full environment-variable list and the
free-tier ephemeral-disk caveat are in
[docs/SETUP.md](docs/SETUP.md#deploying-to-render).

🔐 Environment Variables

**Everything is optional — AEGIS starts with no configuration at all.** A
missing `GROQ_API_KEY` disables policy suggestions and nothing else.

Annotated templates: [`backend/.env.example`](backend/.env.example) and
[`frontend/.env.example`](frontend/.env.example). Full reference in
[docs/SETUP.md](docs/SETUP.md#configuration-reference).

Set `AEGIS_OPERATOR_TOKEN` anywhere the URL is publicly reachable — without it
the control plane accepts anonymous callers. `GET /config` reports which state
a deployment is actually in.

Never commit API keys, wallet credentials or other secrets. `.env` is
gitignored; `.env.example` is the template.

🚀 Future Scope

Already built and no longer "planned": the guard itself, SQLite persistence,
behavioural risk scoring, and ledger anchoring. What is genuinely still ahead:

**Live x402 settlement** — the lifecycle is modelled; moving real funds needs
wallet and key management, signing controls and testing.

**Broadcast-verified anchoring** — the signing path is unit-tested offline; a
funded Base Sepolia key is needed to prove the network accepts it.

**Per-agent policy** — limits are global today. Records already carry an
`agentId`, so scoping policy per agent is a natural next step.

**Transparent proxy mode** — agents currently call `/guard/spend`. Intercepting
an agent's HTTP egress without any code change is the stronger position.

**MCP tool-call governance** — a payment is one kind of agent action; a tool
call is the same interception shape.

**Live data for the remaining screens** — Incident Center, Audit Logs and
Approval Center still read fixtures.

⚠️ Current Limitations

AEGIS is a prototype. Precisely what is real and what is not:

| Component | Status |
|---|---|
| Policy and guardrail engine | **Real** — deterministic, explainable per rule |
| Decision flow and human escalation | **Real** — end to end |
| Credential custody | **Real** — agents never receive a secret |
| Behavioural risk scoring | **Real** — five signals, no LLM |
| Control plane / data plane split | **Real** — enforced in code |
| SQLite persistence | **Real** |
| Hash-linked ledger and verification | **Real** — 25 blocks committed |
| On-chain anchoring | **Built, tested offline.** Signing and signature recovery are unit-tested; the live broadcast needs a funded Base Sepolia key. Run `python anchor_preflight.py` to check |
| x402 payment lifecycle | **Simulated** — the state machine is real, settlement is stubbed. Settled payments are marked `settlement_mode: "simulated"` |
| Value transfer | **Not implemented** — `PAY_TO_ADDRESS` is the zero address. No funds move |
| Incident Center / Audit Logs / Approval Center | **Fixture data.** Set `VITE_HIDE_MOCK_SCREENS=true` to hide them |

Do not put real value through this without wallet and key management,
transaction signing controls, security testing, monitoring and compliance
review.

📚 References

x402 Documentation

x402 Official Site

FastAPI Documentation

React Documentation

SQLite Documentation

👩‍💻 Project

AEGIS — AI Agent Payment Governance

A prototype exploring how autonomous AI agents can perform machine-to-machine payments while remaining subject to configurable financial governance, risk controls, human oversight, and transaction visibility.
