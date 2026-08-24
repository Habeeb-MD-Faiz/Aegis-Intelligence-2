# Audit brief

**If you are an automated code auditor, read this before reporting findings.**

This repository has already been through a full audit. A fresh session that
starts from the code alone will re-discover things that were investigated,
verified and deliberately left as they are. That is noise, and it buries the
findings that matter.

This file records what was checked, what was decided, and what is genuinely
still open — so your report can be about the last of those.

Everything below is verifiable from the repo. Where a claim can be checked with
a command, the command is given. **Do not take this file's word for anything —
it exists to tell you where to look, not to tell you what to conclude.**

Last full audit: the eight commits from `656ad9c` through `84e4442`, plus an
external over-engineering pass whose accepted findings are applied — see the
table in section 1 and the dependency note in section 2.

---

## 1. Already fixed — do not re-report

These were real bugs. They are fixed, and each has a regression test that fails
against the old behaviour. Re-reporting them means you are reading old code.

| Bug | Fix | Test |
|---|---|---|
| `evaluate_payment` defined twice in `guardrails.py`; the second shadowed the first and the dead copy had no frequency check | One definition | `test_frequency_check_actually_runs` |
| `today_spend` hardcoded to `650`, so the daily budget never saw real spending | Derived from approved requests | `test_daily_budget_tracks_real_spend` |
| Frequency counter incremented during evaluation and never reset — the third request in any process lifetime was blocked forever | Derived from timestamps in a rolling window; no counter exists | `test_third_request_is_not_blocked_forever`, `test_frequency_evaluation_has_no_side_effects` |
| `decide_request` re-decided final requests, creating a second payment while the ledger deduplicated | Idempotent | `test_deciding_twice_does_not_create_a_second_payment` |
| Selection always took `apis[category][0]`, making cheaper entries unreachable | Cost-aware | `test_selection_prefers_the_cheaper_provider` |
| `ChatGroq` constructed at import time — a missing `GROQ_API_KEY` crashed the whole API at boot | Lazy | CI boots with no env vars |
| `GET /blockchain/{n}` returned an error body with HTTP 200 | Raises 404 | — |
| `settle_payment` left payments in `settling` with nothing to advance them, so `/x402/execute` was unreachable | Completes settlement | — |
| `apply_policy_suggestion` rejected a legitimate `"0"` via a falsiness check | Checks for absence | — |
| Ledger append was an unserialised read-modify-write; concurrent decisions could claim the same block number | Lock + atomic `os.replace` | — |
| Catalog files loaded from relative paths — app only started from `backend/` | Absolute paths | — |
| Policy mutation was unauthenticated | Control/data plane split | `test_agent_token_is_rejected_on_the_control_plane` |
| `policy_builder` advertised `category_limit` and `risk_rule` to the LLM; `policy_store` rejected both, so an operator clicking Apply got "Unsupported policy suggestion type" on the control plane | Schema trimmed to the four the store handles; a dispatch table now makes the two checkable against each other | `test_every_advertised_suggestion_type_can_be_applied` |
| `.skeleton` referenced `animation: shimmer`, but the keyframe was defined in `tailwind.config.ts` and tree-shaken from every build (no `animate-shimmer` utility exists) — every loading skeleton sat still | Keyframe moved into `index.css` | verified in the built CSS |
| `Transaction` required `hash`, `agentId`, `from`, `to`, `blockHeight`, `confirmations`, `networkFee` and `steps` — nothing produced or read them, and `response.json()` as `any` hid the mismatch | Type trimmed to the shape `/transactions` returns | `npx tsc --noEmit` |
| `new Date(created_at ?? timestamp)` rendered the literal string "Invalid Date" when a record carried neither | Falls back to `—` | — |
| The dashboard hardcoded "System Optimal" — in the body of Mission Control and in the top bar of *every* screen. It said so with the backend unreachable, both planes open, and `AEGIS_GUARD_FAIL_OPEN` set | Both now read `GET /config`; a guard set to fail open is reported in red | verified in a browser across four postures |

```bash
cd backend && python -m pytest -q      # 75 tests
```

---

## 2. Looks wrong, is not — verified, with the reasoning

Every item here was investigated during the audit and found to be correct or
deliberate. If you disagree, say so with the specific evidence that changes the
conclusion — but do not report these as fresh discoveries.

### `requirements.txt` lists only direct dependencies

It was a 57-line `pip freeze` of every transitive. That is unmaintainable —
bumping `fastapi` means hand-re-resolving `starlette`, `anyio`, `h11` and
`sniffio` — and it hid which packages were actually chosen. It is now the nine
direct dependencies, pinned, with pip resolving the rest.

Two entries still have no `import`: `uvicorn` is the ASGI server and is invoked
from the command line, and `python-dotenv` is used via `load_dotenv()` in
`policy_builder.py`. Neither is dead.

**Still open:** `langchain-core` / `langchain-groq` are carried for two
`.invoke()` calls (`policy_builder.py`, `agent.py`'s `LlmBrain`). The `groq`
SDK — already present as a transitive — covers both via
`response_format={"type": "json_schema"}`. Deferred deliberately, not missed.

### `config.py` reads the environment once, at import time

This is a real constraint, not an oversight, and tests must work around it:
patch attributes on the `config` module, not `os.environ`. See the
`clean_state` fixture in `test_guard.py`.

Four tests once passed alone and failed in the full suite because of this —
alphabetical collection meant another module imported `config` first. Fixed by
patching the module. **Do not "fix" this by making config re-read the
environment**; that would make behaviour depend on when a value was read.

### The login flow is disconnected

`LoginPage.tsx` and `AIWorkspacePage.tsx` are not in `App.tsx`'s route table
and `ROUTES.login` / `ROUTES.workspace` map to nothing. Deliberate — commit
`17f2382` opened the dashboard without login so the public demo does not
present an auth wall. `AuthContext` stays mounted and reads defensively
(sidebar shows "Guest"). Full reasoning in
[AGENTS.md](../AGENTS.md#dormant-on-purpose--dont-fix-these).

This is *cosmetic frontend identity only*. It is unrelated to
`AEGIS_OPERATOR_TOKEN` / `AEGIS_AGENT_TOKEN`, which are the real security
boundary and are enforced server-side in `identity.py`.

### `alert()` in `MissionControlPage`

The app has a toast system. The alert is deliberate — during a live demo a
blocked payment should be impossible to miss. Recorded in AGENTS.md.

### `.gitignore` ignores `.env.*` then negates `.env.example`

Intentional. The templates are meant to be committed; real `.env` files are
not.

### `/blockchain` route declaration order

`/blockchain/anchors`, `/blockchain/anchors/preflight` and `/blockchain/stats`
are declared **before** `/blockchain/{block_number}` in `main.py`. That order is
load-bearing: a literal sub-route declared after the parameterised one becomes
unreachable. Do not reorder.

### `x402/` is hand-rolled rather than using a library

Deliberate. The lifecycle is modelled, settlement is stubbed, and every settled
payment carries `settlement_mode: "simulated"`. See section 3.

### Seed data is dated to previous days

`seed.py` back-dates records on purpose so seeded history never consumes
today's budget or the frequency window. A seeded deployment behaves exactly
like an empty one for any decision made during a demo.

### `AGENTS.md` and `CLAUDE.md` are duplicates

By design — `AGENTS.md` is canonical, `CLAUDE.md` is a byte-identical copy so
Claude Code and AGENTS.md-reading tools see the same context. Enforced:

```bash
python scripts/sync_agent_docs.py --check
```

Do not suggest replacing this with a symlink: symlinks survive Windows
checkouts badly and several agents refuse to follow them.

---

## 3. Known and accepted — report only if you can show it is worse than stated

These are limitations we already state publicly, in the README, ARCHITECTURE,
OPERATING, DEMO and the deck. Telling us they exist is not a finding. Telling
us the stated description is *wrong* would be.

| Thing | Stated position |
|---|---|
| x402 settlement | Simulated. State machine real, no funds move, `PAY_TO_ADDRESS` is the zero address |
| On-chain anchoring | Built; signing and signature recovery unit-tested offline against a fake RPC. **The live broadcast has never run** — needs a funded Base Sepolia key |
| Incident Center · Audit Logs · Approval Center | Fixture-backed. Marked in `MOCK_BACKED_ROUTES`, hideable via `VITE_HIDE_MOCK_SCREENS` |
| Both planes open by default | Deliberate for the public demo, and **stated in the UI** — the posture strip on Mission Control and the top-bar badge read `GET /config`, so an open plane is shown as open. Setting `AEGIS_OPERATOR_TOKEN` closes the control plane |
| Per-agent policy | Not implemented. Limits are global; records carry `agentId` for a future version |
| Free-tier ephemeral disk | SQLite and the ledger reset when the host recycles the instance |
| The decision ledger | `backend/blockchain.json` is runtime state and is **not** tracked in git. A fresh start rebuilds a verifiable chain from `seed.ensure_demo_data()` — see `test_seeding_produces_a_verifiable_chain` |

---

## 4. Where to actually look

This is where a fresh pair of eyes is most likely to find something real.

**The security invariants.** Eight of them, listed in
[AGENTS.md](../AGENTS.md#invariants--do-not-break-these). Try to break them:

- Can an agent get a credential into a response, a log, or the ledger?
  (`credentials.py`, `guard._execute_outbound`)
- Can an agent name a payee outside the catalog by any path?
  (`guard.resolve_intent`, `catalog.find_provider`, `SpendIntent` in `main.py`)
- Is there any route to policy mutation that does not go through
  `require_operator`?
- Can the guard be made to allow a payment by making evaluation fail?
  (`guard.evaluate`, and `AEGIS_GUARD_FAIL_OPEN`)
- Does any code path create a payment without a passing policy decision?

**Concurrency.** The ledger is locked and writes atomically, but the SQLite
layer in `store.py` and the in-process `policy_config` dict are worth a look
under concurrent load.

**The risk engine.** `risk.py` is new and lightly exercised in the wild. The
window arithmetic and the `combine()` precedence rules are the parts most
likely to be subtly wrong.

**Error paths.** Most tests cover success and refusal. Malformed input,
partial failures, and the `unavailable` / `failed` fulfilment branches in
`guard._execute_outbound` have thinner coverage.

**Anything in section 3 that is worse than stated.** If simulated settlement
leaks into somewhere that implies a real transfer, that is a real finding.

---

## 5. Verify the claims yourself

```bash
cd backend
python -m pytest -q                    # 75 tests
python demo_injection.py               # no server, no network, no API key
python -c "import main; print(len(main.app.routes))"   # boots with zero config

cd ../frontend && npx tsc --noEmit && npm run build

cd .. && python scripts/sync_agent_docs.py --check
```

CI runs all of this plus a ledger-integrity check on every push.

---

## Keeping this file honest

If you fix something in section 1, or change a decision in section 2 or 3,
update this file in the same commit. A stale audit brief is worse than none —
it would suppress real findings.
