# 🛡️ AEGIS — AI Agent Payment Governance

**A policy enforcement point for autonomous AI-agent payments.**

AEGIS sits between AI agents and the services they pay for. Agents hold no
credentials — they submit an intent, and AEGIS evaluates it against
configurable policy and, only if allowed, makes the paid call itself.

The distinction is the whole design:

> A layer agents *report to* is advisory — an agent that never asks is
> unaffected. A layer that *holds the only credential* is enforceable, and
> refusing needs no cooperation from the agent.

> **We don't stop prompt injection. We make it financially inert.**

Built for problem statement **2.1 — Agent Spend Policy Guard**
(ACTS EDC Brainwave 2026 · team Hacktivists).

---

## ⚡ Quick start

```bash
# Backend — starts with zero configuration
cd backend
pip install -r requirements.txt
uvicorn main:app --reload          # http://127.0.0.1:8000 · API docs at /docs

# Frontend
cd frontend
npm install && npm run dev         # http://127.0.0.1:5173
```

Point the frontend at your local backend by copying `frontend/.env.example`
to `.env.local` and setting `VITE_API_BASE_URL=http://127.0.0.1:8000`.

### See it work in 60 seconds

```bash
cd backend
python demo_injection.py      # no server, no network, no API key needed
python -m pytest -q           # 67 tests
```

The demo runs a real agent through the same prompt-injection attack four times
— holding its own wallet ($5,000 gone), behind AEGIS (refused), against a
legitimate provider (evaluated and explained), and attacking the guard itself
(wrong plane, refused). The agent is compromised in every act.

---

## 🚨 The problem

x402 lets an agent discover a service it has never used, pay for it in one
round trip, and get the resource — no account, no API key, no human in the
provisioning path. That is the feature.

It is also the problem. Spending used to be gated by **provisioning**: a human
vetted a vendor and issued a credential, and that credential *was* the control.
Remove it and an agent with a funded wallet can transact with a provider nobody
approved, at any hour, at any frequency — and the first signal is the balance.

Authorization has to move from provisioning-time to transaction-time. That is
the gap AEGIS fills.

---

## 💡 The solution

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

---

## ✨ Features

| | Feature | What it does |
|---|---|---|
| 🔐 | **Credential custody** | Provider secrets live in the guard, read in exactly one place, and never reach a response, a log line, or the ledger |
| 🚧 | **Catalog-bound payees** | An agent names a task or a known provider — never a URL, an address, or an amount, so injected payment instructions have nowhere to enter |
| 🛡️ | **Five guardrails** | Provider allow list, autonomous approval limit, human review threshold, daily budget, request frequency — each armed or disarmed independently |
| ⚡ | **Three-way decisions** | Approve, escalate to a human, or block. Every rule reports its own verdict and the numbers it saw |
| 📊 | **Behavioural risk scoring** | Five deterministic signals from the agent's own history: first-time provider, novel category, spend deviation, velocity, recent refusals |
| 🔀 | **Control / data plane split** | Policy changes need an operator credential; agent credentials are rejected there by construction, so a compromised agent cannot disarm its own guard |
| 🤖 | **Policy Builder** | Reads the system's own decision history and proposes amendments with evidence counts and confidence. Nothing applies itself |
| ⛓️ | **Tamper-evident ledger** | Hash-linked decision records, verified on read, optionally anchored on Base Sepolia |
| 👤 | **Human-in-the-loop** | Idempotent approvals — deciding twice never creates a second payment |
| 🧯 | **Fail closed** | If the policy engine raises, the answer is no |

---

## 🏗️ Architecture

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

Full detail in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 🔄 Governance scenarios

| Scenario | Outcome |
|---|---|
| Low-risk request within every policy | 🟢 **Approved automatically** — no human touched it |
| Legitimate request above the autonomous threshold | 🟡 **Escalated** to a human |
| Request violating a configured guardrail | 🔴 **Blocked**, with the failing check recorded |
| Payee not in the catalog | 🔴 **Refused before policy evaluation** |
| Agent tries to disarm a guardrail | 🔴 **HTTP 403** — wrong plane |

AEGIS does not simply allow or block all autonomous payments. The middle row is
the point.

---

## 🧰 Technology

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Storage | SQLite — requests, payments and decisions persist across restarts |
| Governance | Custom policy engine + guardrail engine, deterministic |
| Risk | Five behavioural signals, deterministic — no LLM in the scoring path |
| AI | LangChain + Groq — the agent's tool-choice reasoning, and policy suggestions. Never the enforcement decision |
| Payments | x402-style lifecycle — settlement simulated |
| Ledger | SHA-256 hash chain, optionally anchored on Base Sepolia |
| API | REST |
| Deployment | Render (two services) |

---

## 📸 Screenshots

The Command Center, Payment Requests, Guardrails, Policy Builder, Blockchain
Command Center, Transaction Details and Analytics screens all read live backend
data.

<details>
<summary><b>Command Center</b></summary>

![Command Center](screenshots/command_center.png)
</details>

<details>
<summary><b>Payment Requests</b></summary>

![Payment Requests](screenshots/requests.png)
</details>

<details>
<summary><b>Guardrails</b></summary>

![Guardrails](screenshots/guardrails.png)
</details>

<details>
<summary><b>Policy Builder</b></summary>

![Policy Builder](screenshots/policy%20builder.png)
</details>

<details>
<summary><b>Blockchain Command Center</b></summary>

![Blockchain Command Center](screenshots/blockchain.png)
</details>

<details>
<summary><b>Transaction Details</b></summary>

![Transaction Details](screenshots/transaction.png)
</details>

<details>
<summary><b>Human Approval</b></summary>

![Human Approval](screenshots/user_approval.png)
</details>

Regenerate them against a live local stack with
[`scripts/screenshots.py`](scripts/README.md#screenshotspy).

---

## 🎤 Pitch deck

Open [`docs/deck/index.html`](docs/deck/index.html) in any browser and press
<kbd>F11</kbd>. Fifteen slides, keyboard driven (<kbd>←</kbd> <kbd>→</kbd>), no
build step and no network — it works on conference wifi because it never
touches it.

What to say over each slide is in [docs/DEMO.md](docs/DEMO.md).

---

## 🧪 Tests

```bash
cd backend && python -m pytest -q      # 67 tests
```

| File | Covers |
|---|---|
| `test_guard.py` | Guard security properties, and every historical bug as a regression |
| `test_agent.py` | The agent, risk scoring, and the live credential-injected HTTP call |
| `test_anchor.py` | Anchoring: payload, gas, signing, signature recovery, RPC contract |

Each regression test fails against the previous implementation. CI additionally
verifies the API boots with no configuration, the demo runs clean, the frontend
builds, and the committed ledger still verifies.

---

## 📁 Project structure

```
Aegis/
├── AGENTS.md / CLAUDE.md      # agent context (identical; see scripts/)
├── backend/
│   ├── guard.py               # THE ENFORCEMENT POINT — one path money can take
│   ├── credentials.py         # secret custody; agents never hold a key
│   ├── catalog.py             # service catalog + payee boundary
│   ├── identity.py            # control plane / data plane separation
│   ├── guardrails.py          # the policy engine (deterministic)
│   ├── policy_store.py        # active policy configuration
│   ├── risk.py                # behavioural risk scoring (no LLM)
│   ├── policy_builder.py      # LLM proposes amendments; never applies them
│   ├── agent.py               # a real agent whose only spend route is the guard
│   ├── blockchain.py          # hash-linked decision ledger
│   ├── anchor.py              # Base Sepolia anchoring (optional)
│   ├── anchor_preflight.py    # verify anchoring works, spend nothing
│   ├── store.py               # SQLite persistence
│   ├── request_history.py     # records + derived spend/frequency
│   ├── seed.py                # historical demo data
│   ├── config.py              # env-driven configuration
│   ├── selector.py            # legacy /execute-task → guard
│   ├── main.py                # FastAPI routes
│   ├── demo_injection.py      # ▶ the demo — runs without a server
│   ├── test_guard.py · test_agent.py · test_anchor.py    # 67 tests
│   └── x402/                  # payment lifecycle (settlement simulated)
├── frontend/
│   ├── src/config.ts          # single source for API URL + credentials
│   └── src/                   # pages, services, components
├── docs/
│   ├── ARCHITECTURE.md        # how the guard works
│   ├── API.md                 # endpoint reference
│   ├── SETUP.md               # install, config, deployment
│   ├── OPERATING.md           # using the dashboard
│   ├── DEMO.md                # demo runbook — what you say
│   └── deck/index.html        # ▶ the pitch deck — what you show
├── scripts/                   # agent-doc sync, screenshot capture
└── screenshots/
```

---

## 📚 Documentation

| Doc | For |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | How enforcement works, and why it's a guard rather than a dashboard |
| [API.md](docs/API.md) | Every endpoint, auth, request/response examples |
| [SETUP.md](docs/SETUP.md) | Install, configure, deploy, troubleshoot |
| [OPERATING.md](docs/OPERATING.md) | Operator guide — reading decisions, approving requests, guardrails |
| [DEMO.md](docs/DEMO.md) | Demo runbook and anticipated questions |
| [deck/index.html](docs/deck/index.html) | The pitch deck — 15 slides, opens offline in any browser |

---

## 🤖 Working on this with a coding agent

[`AGENTS.md`](AGENTS.md) is the context file: what AEGIS is, the invariants that
must not be broken, the module map, how to run and test, current
real-vs-simulated state, and what to do next. Clone the repo, open any agent,
and it has the full picture.

`CLAUDE.md` is a byte-identical copy for Claude Code, and Cursor, Copilot and
Windsurf read pointer files that defer to `AGENTS.md` — so there is exactly one
place to edit. `scripts/sync_agent_docs.py` keeps them identical and CI fails
if they drift. See [scripts/README.md](scripts/README.md).

---

## 💳 x402

x402 is an HTTP-native approach to programmatic payments built on the
`402 Payment Required` status. AEGIS models its lifecycle:

```
payment_required → authorized → verified → settling → settled
```

The state machine is real. **Settlement is simulated** — `PAY_TO_ADDRESS` is
the zero address and no funds move. Settled payments carry
`settlement_mode: "simulated"` so the API never implies otherwise.

The guard is the gateway this project originally listed as future work: it sits
between agents and providers rather than beside them, so it cannot be bypassed
by an agent that simply declines to ask.

---

## 🌐 Service catalog

`backend/api_catalog.json` holds providers, per-request costs, categories and
descriptions across research, travel, maps, email, documents, image generation,
video generation, speech, translation, weather, web search, code and payments.

Selection is **cost-aware** — the cheapest service that satisfies a category
wins, so cheaper providers are reachable rather than shadowed by the first
catalog entry.

The catalog is also the security boundary: an agent can only name something in
it, which is what stops "pay this address I found in a document".

---

## ☁️ Deployment

Frontend and backend deploy as two services on Render. Root directories, build
and start commands, the full environment-variable list and the free-tier
ephemeral-disk caveat are in
[docs/SETUP.md](docs/SETUP.md#deploying-to-render).

---

## 🔐 Configuration

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

---

## ⚠️ What is real and what is not

AEGIS is a prototype. Precisely:

| Component | Status |
|---|---|
| Policy and guardrail engine | ✅ **Real** — deterministic, explainable per rule |
| Decision flow and human escalation | ✅ **Real** — end to end |
| Credential custody | ✅ **Real** — agents never receive a secret |
| Catalog-bound payees | ✅ **Real** — enforced before policy evaluation |
| Behavioural risk scoring | ✅ **Real** — five signals, no LLM |
| Control / data plane split | ✅ **Real** — enforced in code |
| SQLite persistence | ✅ **Real** |
| Hash-linked ledger and verification | ✅ **Real** — 25 blocks committed |
| Analytics | ✅ **Real** — reads live decisions |
| On-chain anchoring | 🟡 **Built, tested offline.** Signing and signature recovery are unit-tested; the live broadcast needs a funded Base Sepolia key — run `python anchor_preflight.py` |
| x402 payment lifecycle | 🟡 **Simulated** — state machine real, settlement stubbed |
| Value transfer | 🔴 **Not implemented** — no funds move |
| Incident Center / Audit Logs / Approval Center | 🔴 **Fixture data** — hide with `VITE_HIDE_MOCK_SCREENS=true` |

Do not put real value through this without wallet and key management,
transaction signing controls, security testing, monitoring and compliance
review.

---

## 🚀 What's next

Already built and no longer planned: the guard, SQLite persistence,
behavioural risk scoring, ledger anchoring. Genuinely ahead:

- **Transparent proxy mode** — agents call `/guard/spend` today. Intercepting an
  agent's HTTP egress with no code change on their side is the stronger
  position.
- **Broadcast-verified anchoring** — the signing path is unit-tested; a funded
  Base Sepolia key would prove the network accepts it.
- **Per-agent policy** — limits are global; records already carry `agentId`.
- **Live x402 settlement** — needs wallet and key management first.
- **MCP tool-call governance** — a payment is one kind of agent action; a tool
  call is the same interception shape.
- **Live data for the remaining three screens.**

---

## 📚 References

- [x402 documentation](https://x402.gitbook.io/x402) — protocol architecture and the HTTP 402 flow
- [x402 on GitHub](https://github.com/coinbase/x402) — reference implementations
- [Base Sepolia](https://docs.base.org/chain/network-information) — the testnet used for ledger anchoring
- [FastAPI](https://fastapi.tiangolo.com/) · [React](https://react.dev/) · [Vite](https://vite.dev/) · [Tailwind CSS](https://tailwindcss.com/)
- [SQLite](https://www.sqlite.org/docs.html) · [LangChain](https://python.langchain.com/) · [Groq](https://console.groq.com/docs)

---

## 👩‍💻 About

**AEGIS — AI Agent Payment Governance.** A prototype exploring how autonomous
AI agents can perform machine-to-machine payments while remaining subject to
configurable financial governance, risk controls, human oversight and
transaction visibility.

Team **Hacktivists** · University School of Automation and Robotics ·
ACTS EDC Brainwave 2026.
