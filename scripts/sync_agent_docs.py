#!/usr/bin/env python3
"""
Keep the agent context files in sync.

AGENTS.md is canonical. CLAUDE.md is a byte-identical copy of it, so Claude
Code and every AGENTS.md-reading tool (OpenCode, Codex, Antigravity, Zed,
Jules, Cursor via its rules file, and others) see exactly the same context.

    python scripts/sync_agent_docs.py           # copy AGENTS.md -> CLAUDE.md
    python scripts/sync_agent_docs.py --check   # exit 1 if they differ

The --check mode runs in CI, so the two cannot drift apart on main.

Pure stdlib, no dependencies, works on Windows, macOS and Linux. Deliberately
not a symlink: symlinks survive git badly on Windows checkouts and several
editors and agents refuse to follow them.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "AGENTS.md"
MIRROR = ROOT / "CLAUDE.md"


def read(path: Path) -> str:
    # newline="" preserves the file's own line endings so a Windows checkout
    # does not report a false mismatch. Path.read_text gained a newline
    # argument only in 3.13, so use open() — this must run on 3.11.
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the files match; do not write anything",
    )
    args = parser.parse_args()

    if not CANONICAL.exists():
        print(f"error: {CANONICAL.name} is missing — it is the canonical file.")
        return 1

    canonical = read(CANONICAL)

    if args.check:
        if not MIRROR.exists():
            print(f"✗ {MIRROR.name} is missing.")
            print("  Run: python scripts/sync_agent_docs.py")
            return 1

        if read(MIRROR) != canonical:
            print(f"✗ {MIRROR.name} has drifted from {CANONICAL.name}.")
            print("  AGENTS.md is canonical. Put your edit there, then run:")
            print("    python scripts/sync_agent_docs.py")
            return 1

        print(f"✓ {CANONICAL.name} and {MIRROR.name} are identical.")
        return 0

    if MIRROR.exists() and read(MIRROR) == canonical:
        print(f"✓ {MIRROR.name} already matches {CANONICAL.name}. Nothing to do.")
        return 0

    with open(MIRROR, "w", encoding="utf-8", newline="") as handle:
        handle.write(canonical)
    print(f"✓ Wrote {MIRROR.name} from {CANONICAL.name}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
