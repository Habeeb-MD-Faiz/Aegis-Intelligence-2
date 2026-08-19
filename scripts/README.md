# scripts

## `sync_agent_docs.py`

Keeps the agent context files identical.

`AGENTS.md` is canonical. `CLAUDE.md` is a byte-identical copy so Claude Code
gets the same context as every AGENTS.md-reading tool.

```bash
python scripts/sync_agent_docs.py           # copy AGENTS.md -> CLAUDE.md
python scripts/sync_agent_docs.py --check   # exit 1 if they differ
```

Enforced in two places, so drift can't land:

- **CI** — the `agent-docs` job runs `--check` on every push and PR.
- **Optional git hook** — catch it before you push:

  ```bash
  git config core.hooksPath scripts/hooks
  ```

Stdlib only, no dependencies, runs on Python 3.11+, works on Windows.

## Which file does each tool read?

| Tool | Reads |
|---|---|
| OpenCode, Codex, Antigravity, Zed, Jules, Aider | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursor/rules/aegis.mdc` → points at `AGENTS.md` |
| GitHub Copilot | `.github/copilot-instructions.md` → points at `AGENTS.md` |
| Windsurf | `.windsurfrules` → points at `AGENTS.md` |

Only `AGENTS.md` carries the real content. Everything else is a copy or a
pointer, so there is exactly one place to edit.
