# Setup and deployment

## Prerequisites

- Python 3.11+
- Node.js 18+
- No database server — AEGIS uses SQLite, which needs no setup

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Runs on `http://127.0.0.1:8000`. Interactive API docs at `/docs`.

**It starts with no configuration at all.** Every environment variable is
optional — a missing `GROQ_API_KEY` disables policy suggestions and nothing
else. Copy `.env.example` to `.env` when you want to change something.

On first boot AEGIS seeds a handful of historical requests so the dashboard
isn't empty. They're dated to previous days, so they never consume today's
budget or frequency window.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://127.0.0.1:5173`.

By default it talks to the **deployed** backend. To point it at your local one:

```bash
cp .env.example .env.local
# set VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Tests

```bash
cd backend
python -m pytest -q        # 67 tests
```

| File | Covers |
|---|---|
| `test_guard.py` | guard security properties and every fixed bug |
| `test_agent.py` | the agent, risk scoring, and the live credential-injected call |
| `test_anchor.py` | anchoring: payload, signing, signature recovery, RPC contract |

Each regression test fails against the previous implementation.

## The demo

```bash
cd backend
python demo_injection.py
```

Runs the prompt-injection scenario four ways. No server, no network — it can't
fail because a dyno was asleep. See [DEMO.md](DEMO.md) for the run of show.

---

## Configuration reference

Full annotated list in `backend/.env.example`. The ones that matter:

### Identity

| Variable | Effect |
|---|---|
| `AEGIS_OPERATOR_TOKEN` | Locks the control plane. **Set this anywhere public.** |
| `AEGIS_AGENT_TOKEN` | Locks the data plane |

Unset means that plane accepts anonymous callers. The agent-vs-operator
*separation* holds either way — an agent credential is rejected on the control
plane regardless. `GET /config` reports which state you're in.

### Provider endpoints

`AEGIS_ENDPOINT_<PROVIDER>` — the URL the guard calls for a provider. Without
one, the guard authorizes and injects the credential but fulfils in simulation
and reports `fulfilment: "simulated"`.

```bash
AEGIS_ENDPOINT_BLOOMBERG=https://api.example.com/v1/query
```

### Provider credentials

`AEGIS_CREDENTIAL_<PROVIDER>` — the secrets agents never receive. Provider name
uppercased with spaces as underscores:

```bash
AEGIS_CREDENTIAL_BLOOMBERG=sk-live-...
AEGIS_CREDENTIAL_ALPHA_VANTAGE=...
```

### Ledger anchoring

| Variable | Default |
|---|---|
| `AEGIS_CHAIN_PRIVATE_KEY` | *(empty — anchoring off)* |
| `AEGIS_CHAIN_RPC_URL` | `https://sepolia.base.org` |
| `AEGIS_ANCHOR_EVERY` | `5` blocks |

Needs a funded **Base Sepolia testnet** key. This writes a hash, not value —
but use a throwaway key regardless, and never a mainnet one.

Check it works before you rely on it — this never broadcasts:

```bash
cd backend && python anchor_preflight.py
```

Everything about anchoring is unit-tested offline. The one thing tests cannot
prove is that the network accepts the transaction, which is exactly what
preflight checks.

Without a key, anchoring is skipped and reported as disabled. AEGIS never claims
an anchor it did not write.

### Storage

| Variable | Default |
|---|---|
| `AEGIS_DB_FILE` | `aegis.db` |
| `AEGIS_LEDGER_FILE` | `blockchain.json` |
| `AEGIS_SEED_DEMO_DATA` | `true` |

### Guard behaviour

| Variable | Default | Notes |
|---|---|---|
| `AEGIS_GUARD_TIMEOUT` | `10` | seconds for outbound calls |
| `AEGIS_GUARD_FAIL_OPEN` | `false` | **leave false** — a guard that opens when its own evaluation crashes is not a guard |

### Frontend

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | backend URL |
| `VITE_OPERATOR_TOKEN` | must match `AEGIS_OPERATOR_TOKEN` |
| `VITE_HIDE_MOCK_SCREENS` | hides fixture-backed screens — worth setting before a demo |

---

## Deploying to Render

Two services from one repo.

### Backend (Web Service)

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

Environment variables to set:

```
AEGIS_OPERATOR_TOKEN=<generate a long random string>
AEGIS_CORS_ORIGINS=https://your-frontend.onrender.com
GROQ_API_KEY=<optional>
```

> **Free tier caveat.** The dyno sleeps, and its disk is ephemeral — SQLite and
> the ledger file reset when the instance is recycled. Seeded data means the
> dashboard is never empty, but transactions made before a sleep won't survive
> it. Attach a persistent disk, or hit the URL a few minutes before a demo.

### Frontend (Static Site)

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command | `npm install && npm run build` |
| Publish directory | `dist` |

```
VITE_API_BASE_URL=https://your-backend.onrender.com
VITE_HIDE_MOCK_SCREENS=true
```

`VITE_` variables are baked in at build time — changing one requires a rebuild,
not just a restart.

---

## Troubleshooting

**Backend won't start: `FileNotFoundError` on a JSON file**
Shouldn't happen any more — catalog paths are absolute. If you see it, you're on
an old checkout that only ran from `backend/`.

**`403 Agent credentials cannot modify policy`**
Working as intended. Use the operator token for policy and guardrail changes.

**Guardrail toggle fails in the UI with "Operator credential required"**
Set `VITE_OPERATOR_TOKEN` to match the backend's `AEGIS_OPERATOR_TOKEN` and
rebuild the frontend.

**Policy suggestions return an empty list with a message**
`GROQ_API_KEY` is unset, or there isn't enough history yet. Expected — nothing
else is affected.

**Anchoring never happens**
Check `GET /blockchain/anchors`. Anchoring needs a key, and only fires every
`AEGIS_ANCHOR_EVERY` blocks. Failures are logged and deliberately non-fatal.

**Everything reset after a restart**
Ephemeral disk on a free host. See the Render caveat above.

**A screen's numbers don't match transactions I just made**
Analytics reads live data now. Incident Center, Audit Logs and Approval Center
are still fixture-backed — set `VITE_HIDE_MOCK_SCREENS=true`, or see
`MOCK_BACKED_ROUTES` in `frontend/src/constants/nav.ts`.
