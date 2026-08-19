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

## `screenshots.py`

Regenerates the README screenshots from a live local stack.

```bash
python scripts/screenshots.py --activity
```

Run it on a **desktop machine**, not a headless CI box: headless browsers
frequently fail to load the Material Symbols icon font, and every nav item
comes out as its ligature name ("space_dashboard" instead of the icon). The
script detects that and refuses rather than writing broken images.

Full setup instructions are in the file's docstring — it needs the backend
running with CORS open to the preview server, and the frontend built against
that backend.

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
