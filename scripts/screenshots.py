#!/usr/bin/env python3
"""
Regenerate the README screenshots from a live local stack.

Headless environments often fail to load the Material Symbols icon font over
the network, which makes every nav item render as its ligature name
("space_dashboard" instead of the icon). This script fetches the font itself
and injects it as a data URI, so it produces correct screenshots headlessly —
no desktop browser needed. If the font cannot be fetched or does not take, it
refuses to write rather than committing broken images.

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
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots"

# route -> committed screenshot filename, matching what README.md embeds
PAGES = [
    ("#/", "mission_control"),
    ("#/command-center", "command_center"),
    ("#/payments", "requests"),
    ("#/guardrails", "guardrails"),
    ("#/policies", "policy_builder"),
    ("#/blockchain", "blockchain"),
    ("#/transactions", "transaction"),
    ("#/approvals", "user_approval"),
    ("#/analytics", "analytics"),
]

# Material Symbols, fetched once and injected as a data URI. Loading it from
# fonts.googleapis.com inside a headless browser is the thing that used to make
# these screenshots come out as ligature text.
FONT_CSS_URL = (
    "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined"
)

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


def icon_font_css() -> str:
    """
    Material Symbols as a self-contained @font-face, or "" if unreachable.

    The !important is load-bearing: the app already declares its own
    @font-face pointing at fonts.gstatic.com, and in a headless browser that
    one resolves but never paints. Ours has to win.
    """

    import base64
    import re

    try:
        request = urllib.request.Request(
            FONT_CSS_URL,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        css = urllib.request.urlopen(request, timeout=30).read().decode()

        match = re.search(r"https://fonts\.gstatic\.com[^)]+", css)

        if not match:
            return ""

        font = urllib.request.urlopen(match.group(0), timeout=60).read()

    except Exception as exc:
        print(f"  ! could not fetch the icon font: {exc}")
        return ""

    encoded = base64.b64encode(font).decode()

    return (
        "@font-face{font-family:'Material Symbols Outlined';font-style:normal;"
        f"font-weight:400;src:url(data:font/ttf;base64,{encoded}) "
        "format('truetype');}"
        ".material-symbols-outlined{font-family:'Material Symbols Outlined' "
        "!important;}"
    )


# Whether an icon rendered cannot be read from innerText — that returns the
# ligature name ("space_dashboard") whether it painted as a glyph or as the
# literal word. Measuring the box is the only honest check: a glyph is roughly
# square at the font size, the spelled-out word is far wider.
GLYPH_CHECK = """() => {
  const el = document.querySelector('.material-symbols-outlined');
  if (!el) return { ok: false, reason: 'no icon element on the page' };
  const width = el.getBoundingClientRect().width;
  return { ok: width > 0 && width < 40, reason: `glyph box ${width.toFixed(1)}px` };
}"""


def capture(app: str, scale: int) -> int:
    try:
        from playwright.sync_api import sync_playwright

    except ImportError:
        print("Playwright is not installed.")
        print("  pip install playwright && playwright install chromium")
        return 1

    OUT.mkdir(exist_ok=True)

    print("Fetching the icon font ...")
    font_css = icon_font_css()

    with sync_playwright() as p:
        # Some environments ship a Chromium that Playwright did not download
        # itself, so its expected build number will not match. Point at it
        # with AEGIS_CHROMIUM rather than re-downloading a browser.
        executable = os.environ.get("AEGIS_CHROMIUM")

        browser = (
            p.chromium.launch(executable_path=executable)
            if executable
            else p.chromium.launch()
        )
        page = browser.new_page(
            viewport={"width": 1600, "height": 1000},
            device_scale_factor=scale,
        )

        for route, name in PAGES:
            page.goto(f"{app}/{route}", wait_until="networkidle")

            if font_css:
                page.add_style_tag(content=font_css)

            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(2500)

            body = page.inner_text("body")

            if "Couldn't load this data" in body or "Failed to fetch" in body:
                print(f"  ✗ {name}: the page could not reach the API.")
                print("    Check VITE_API_BASE_URL and AEGIS_CORS_ORIGINS.")
                browser.close()
                return 1

            if "Backend unreachable" in body:
                print(f"  ✗ {name}: the backend is not reachable from the browser.")
                print("    Check VITE_API_BASE_URL and AEGIS_CORS_ORIGINS.")
                browser.close()
                return 1

            glyph = page.evaluate(GLYPH_CHECK)

            if not glyph["ok"]:
                print(f"  ✗ {name}: the icon font did not render ({glyph['reason']}).")
                print("    Every nav item would come out as ligature text.")
                browser.close()
                return 1

            page.screenshot(path=str(OUT / f"{name}.png"))
            print(f"  ✓ {name}.png")

        browser.close()

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
