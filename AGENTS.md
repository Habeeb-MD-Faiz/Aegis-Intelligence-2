# AEGIS — agent context

<!--
  CANONICAL SOURCE. CLAUDE.md is a byte-identical copy of this file.
  Edit this file, then run:  python scripts/sync_agent_docs.py
  CI fails if the two drift apart.
-->

Read this first. It is written for a coding agent picking the repo up cold,
and it tells you what the project is, what must not be broken, and where to
look.

---

## What this is

A **policy enforcement point** for autonomous AI-agent payments. Agents hold no
payment credentials — they submit an intent, and AEGIS evaluates it and, only
if policy allows, makes the paid call itself using a secret the agent has never
seen.

The distinction that matters:

> A layer agents *report to* is advisory — an agent that never asks is
> unaffected. A layer that *holds the only credential* is enforceable, and
> refusing needs no cooperation from the agent.

Built for hackathon problem statement **2.1 — Agent Spend Policy Guard**
(ACTS EDC Brainwave 2026, team Hacktivists).

The one-line thesis, used throughout the docs and the deck:

> **We don't stop prompt injection. We make it financially inert.**

---

## Run it

```bash
# backend — starts with zero configuration
cd backend
pip install -r requirements.txt
uvicorn main:app --reload            # http://127.0.0.1:8000, docs at /docs

# tests — 67, all should pass
python -m pytest -q

# the demo — no server, no network, no API key needed
python demo_injection.py

# frontend
cd frontend && npm install && npm run dev    # http://127.0.0.1:5173
```

Point the frontend at a local backend with `VITE_API_BASE_URL` in
`frontend/.env.local` (see `.env.example`).

---

## Invariants — do not break these

These are the design, not preferences. If a change violates one, the change is
wrong.

1. **Agents never hold credentials.** Secrets live in `credentials.py`, are read
   in exactly one place (`guard._execute_outbound`), and must never reach a
   response, a log line, or the ledger. There is a test for this.

2. **Agents can only name catalog providers.** No URL, no wallet address, no
   caller-supplied amount — look at `SpendIntent` in `main.py` and note what is
   absent. An unknown payee is refused in `guard.resolve_intent()` *before*
   policy evaluation. This is what stops injected payment instructions.

3. **Fail closed.** If the policy engine raises, the answer is no.
   `AEGIS_GUARD_FAIL_OPEN` exists but must stay off.

4. **The control plane is not reachable by agents.** Policy mutation requires an
   operator credential; an agent credential is rejected with 403 *whether or not*
   tokens are configured. A compromised agent must never be able to widen its
   own authority.

5. **No LLM in the enforcement path.** Guardrails and risk scoring are
   deterministic — the same request must score the same way twice, and an
   operator must be able to see which rule or signal fired. An LLM proposes
   policy (`policy_builder.py`); it never decides whether to release money.

6. **Nothing self-applies.** Policy suggestions are recommendations until a human
   applies them on the control plane.

7. **Never claim something that isn't true.** If anchoring isn't configured, the
   API says so. Settled payments are labelled `settlement_mode: "simulated"`.
   Docs separate real from simulated. Keep it that way — the honesty is a
   feature, and it is the thing that survives scrutiny.

8. **Decisions are idempotent.** Deciding an already-final request must not
   create a second payment.

---

## Layout

### Backend (`backend/`, FastAPI)

| File | Role |
|---|---|
| `guard.py` | **The enforcement point.** The one path money can take. Start here. |
| `credentials.py` | Secret custody. Read in one place, never serialized. |
| `catalog.py` | Service catalog, cost-aware selection, the payee boundary. |
| `identity.py` | Control plane / data plane separation. |
| `guardrails.py` | The policy engine — five checks, deterministic, explainable. |
| `policy_store.py` | Active policy configuration. |
| `risk.py` | Behavioural risk scoring — five signals, no LLM. |
| `policy_builder.py` | LLM proposes policy amendments. Never applies them. |
| `agent.py` | A real agent loop whose only spend route is the guard. |
| `blockchain.py` | Hash-linked decision ledger, verified on read. |
| `anchor.py` | Base Sepolia anchoring. Optional, best-effort. |
| `anchor_preflight.py` | CLI: check anchoring works, spend nothing. |
| `store.py` | SQLite persistence. |
| `request_history.py` | Records plus derived spend / frequency figures. |
| `seed.py` | Historical demo data, dated to previous days. |
| `config.py` | All configuration, env-driven. |
| `selector.py` | Legacy `/execute-task` entry point — delegates to the guard. |
| `main.py` | FastAPI routes. |
| `demo_injection.py` | The prompt-injection demo. Runs without a server. |
| `x402/` | Payment lifecycle. Settlement is simulated. |

### Frontend (`frontend/`, React + TypeScript + Vite + Tailwind)

Hand-rolled — no router, no query library, no chart library. `RouterContext` is
~50 lines over `window.location.hash`; charts are hand-drawn SVG; `useAsync` is
the loading/error/refetch hook used by every page.

- `src/config.ts` — single source for API URL and operator credential.
- `src/services/` — one module per domain. Some read the backend, some still
  read fixtures (see below).
- `src/constants/nav.ts` — `MOCK_BACKED_ROUTES` marks fixture-backed screens.

### Docs (`docs/`)

`ARCHITECTURE.md` (how the guard works) · `API.md` (every endpoint) ·
`SETUP.md` (install, config, deploy) · `OPERATING.md` (using the dashboard) ·
`DEMO.md` (run of show, Q&A prep) · `deck/index.html` (the pitch deck).

---

## Current state

**Real:** policy and guardrail engine, decision flow and human escalation,
credential custody, catalog-bound payees, behavioural risk scoring, control /
data plane split, SQLite persistence, hash-linked ledger and verification,
Analytics (reads live decisions).

**Built but not fully proven:** on-chain anchoring. Payload encoding, gas
estimation, transaction construction, signing and **signature recovery** are
unit-tested offline against a fake JSON-RPC endpoint. The live broadcast has
never run — it needs a funded Base Sepolia key. `anchor_preflight.py` checks
readiness without broadcasting.

**Simulated:** the x402 payment lifecycle. The state machine is real;
settlement is stubbed and `PAY_TO_ADDRESS` is the zero address. No funds move.

**Fixture-backed:** Incident Center, Audit Logs, Approval Center. Marked in
`MOCK_BACKED_ROUTES`; hide with `VITE_HIDE_MOCK_SCREENS=true`.

---

## Tests

67 tests, all passing. Run `python -m pytest -q` from `backend/`.

| File | Covers |
|---|---|
| `test_guard.py` | Guard security properties, and every historical bug as a regression |
| `test_agent.py` | The agent, risk scoring, and the live credential-injected HTTP call |
| `test_anchor.py` | Anchoring: payload, gas, signing, signature recovery, RPC contract |

Two things worth knowing before you add tests:

- `config.py` reads the environment **once at import time**. Tests that depend
  on tokens must set attributes on the `config` module (see the `clean_state`
  fixture in `test_guard.py`), not on `os.environ` — otherwise they pass alone
  and fail in the full suite depending on collection order.
- The live-call tests stand up a real local HTTP server. Keep them hermetic; no
  test may reach the public internet.

Expected of a change: a bug fix gets a regression test that fails against the
old behaviour. A security property gets a test that proves it.

---

## Next steps, roughly in order of value

1. **Transparent proxy mode.** Agents call `/guard/spend` today. Intercepting an
   agent's HTTP egress with no code change on their side is the stronger
   position and the thing that makes this infrastructure.
2. **Prove anchoring end to end.** Fund a Base Sepolia key, run
   `anchor_preflight.py`, then a real broadcast. Update the honesty tables in
   `README.md`, `docs/ARCHITECTURE.md`, `docs/OPERATING.md`, `docs/DEMO.md` and
   deck slides 10 and 14 when it lands.
3. **Per-agent policy.** Limits are global; records already carry `agentId`.
4. **Live data for the remaining three screens.**
5. **Live x402 settlement** — needs wallet and key management first.
6. **MCP tool-call governance** — same interception shape as payments.

---

## Conventions

- **Comments explain *why*, not *what*.** Several modules carry a docstring
  explaining what was wrong before and why the current shape exists — that
  context is deliberate; preserve it when editing.
- **Match the surrounding style.** The codebase is plain and explicit. No
  frameworks or abstractions added without a clear reason.
- **Config over constants.** Anything environment-dependent goes in `config.py`
  with an env override and an entry in `.env.example`.
- **Commits** describe what changed and why, in prose. Reference the behaviour,
  not the file list.
- **Update the docs in the same change.** The honesty tables appear in five
  places (`README.md`, `docs/ARCHITECTURE.md`, `docs/OPERATING.md`,
  `docs/DEMO.md`, deck slide 14). If you change what is real, change all of
  them.
- **Don't commit** build artifacts, `aegis.db`, or anything matching `.env`.

---

## Gotchas

- **`GET /blockchain/{n}` route order.** `/blockchain/anchors` and
  `/blockchain/stats` are declared before `/blockchain/{block_number}` in
  `main.py`. Adding a new literal sub-route *after* the parameterised one will
  make it unreachable.
- **Ledger writes are locked and atomic.** `create_blockchain_record` holds
  `_chain_lock` for the whole read-modify-write and saves via a temp file plus
  `os.replace`. Don't add a write path that bypasses it.
- **Seed data is dated to previous days** on purpose, so it never consumes
  today's budget or frequency window. Keep that if you change `seed.py`.
- **Frequency and spend are derived from timestamps**, not counters. There is no
  counter to reset — an earlier version had one that never reset and blocked the
  third request forever.
- **`VITE_` variables are baked in at build time.** Changing one needs a
  rebuild, not a restart.
- **Render's free tier has an ephemeral disk.** SQLite and the ledger reset when
  the instance recycles. Seeding means the dashboard is never empty.

---

## Keeping this file in sync

`AGENTS.md` is canonical. `CLAUDE.md` is a byte-identical copy so Claude Code
picks up the same context. Other tools read pointer files that defer here:
`.cursor/rules/aegis.mdc`, `.github/copilot-instructions.md`, `.windsurfrules`.

After editing this file:

```bash
python scripts/sync_agent_docs.py
```

CI fails if `AGENTS.md` and `CLAUDE.md` differ, so drift cannot land.
