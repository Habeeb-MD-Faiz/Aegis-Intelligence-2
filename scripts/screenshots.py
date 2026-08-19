#!/usr/bin/env python3
"""
Regenerate the README screenshots from a live local stack.

Run this on a machine with a normal desktop browser. Headless environments
often fail to load the Material Symbols icon font, which makes every nav item
render as its ligature name ("space_dashboard" instead of the icon) — the
screenshots come out looking broken even though the app is fine.

    # 1. terminal one — backend, seeded, CORS open to the preview server
    cd backend
    AEGIS_CORS_ORIGINS=http://127.0.0.1:4173 uvicorn main:app --port 8000

    # 2. terminal two — build the frontend against it and preview
    cd frontend
    VITE_API_BASE_URL=http://127.0.0.1:8000 npm run build
    npm run preview -- --port 4173

    # 3. terminal three
    pip install playwright && playwright install chromium
    python scripts/screenshots.py

Add --activity to push a few requests through the guard first, so the
dashboards have something real to show.
"""

import argparse
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots"

# route -> committed screenshot filename
PAGES = [
    ("#/", "command_center"),
    ("#/payments", "requests"),
    ("#/guardrails", "guardrails"),
    ("#/policies", "policy builder"),
    ("#/blockchain", "blockchain"),
    ("#/transactions", "transaction"),
    ("#/approvals", "user_approval"),
]

# A few tasks that exercise different outcomes: auto-approved, escalated,
# and one that trips the provider allow list.
ACTIVITY = [
    "research tesla quarterly earnings",
    "check weather for the delhi office",
    "find the route from delhi to jaipur",
    "book flights from delhi to singapore",
    "generate marketing images for the launch",
]


def post(url: str, payload: dict) -> None:
    import json

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    try:
        urllib.request.urlopen(request, timeout=15).read()

    except urllib.error.HTTPError:
        # A blocked request is a 403 — that is a valid outcome to screenshot.
        pass


def seed_activity(api: str) -> None:
    print(f"Pushing {len(ACTIVITY)} tasks through {api} ...")

    for task in ACTIVITY:
        post(f"{api}/execute-task", {"message": task})

    print("  done")


def capture(app: str, scale: int) -> int:
    try:
        from playwright.sync_api import sync_playwright

    except ImportError:
        print("Playwright is not installed.")
        print("  pip install playwright && playwright install chromium")
        return 1

    OUT.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 1600, "height": 1000},
            device_scale_factor=scale,
        )

        broken_icons = False

        for route, name in PAGES:
            page.goto(f"{app}/{route}", wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(2500)

            body = page.inner_text("body")

            if "Couldn't load this data" in body or "Failed to fetch" in body:
                print(f"  ✗ {name}: the page could not reach the API.")
                print("    Check VITE_API_BASE_URL and AEGIS_CORS_ORIGINS.")
                browser.close()
                return 1

            if "space_dashboard" in body:
                broken_icons = True

            page.screenshot(path=str(OUT / f"{name}.png"))
            print(f"  ✓ {name}.png")

        browser.close()

    if broken_icons:
        print()
        print("⚠️  The icon font did not render — nav items show as ligature")
        print("   text. These screenshots are not usable. Run this on a")
        print("   desktop machine with normal font loading.")
        return 1

    print(f"\nWrote {len(PAGES)} screenshots to {OUT}/")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="backend URL")
    parser.add_argument("--app", default="http://127.0.0.1:4173", help="frontend URL")
    parser.add_argument("--scale", type=int, default=2, help="device scale factor")
    parser.add_argument(
        "--activity",
        action="store_true",
        help="push a few requests through the guard before capturing",
    )
    args = parser.parse_args()

    try:
        urllib.request.urlopen(args.api, timeout=10).read()

    except Exception:
        print(f"Backend not reachable at {args.api}. Start it first — see the")
        print("instructions at the top of this file.")
        return 1

    if args.activity:
        seed_activity(args.api)

    return capture(args.app, args.scale)


if __name__ == "__main__":
    sys.exit(main())
