# Copilot instructions

The full agent context for this repository is in **[AGENTS.md](../AGENTS.md)**
at the repo root. Read it before suggesting changes.

Key invariants that must never be violated:

- Agents never hold payment credentials — secrets live in `backend/credentials.py`
  and must not reach a response, a log line, or the ledger.
- Agents can only name providers from the catalog. No URLs, addresses or
  caller-supplied amounts.
- Fail closed: if the policy engine raises, the answer is no.
- Policy mutation requires an operator credential; agent credentials are
  rejected on the control plane by construction.
- No LLM in the enforcement or risk-scoring path — both must be deterministic.
- Never claim a capability the code does not have.

Run tests with `cd backend && python -m pytest -q` (67 tests).
