# Pitch deck

`index.html` — a self-contained 15-slide deck for the AEGIS pitch.

## Presenting it

Open `index.html` in any browser and go full screen (<kbd>F11</kbd>, or
<kbd>⌃⌘F</kbd> on macOS).

| Key | Action |
|---|---|
| <kbd>→</kbd> <kbd>↓</kbd> <kbd>Space</kbd> <kbd>PgDn</kbd> | next slide |
| <kbd>←</kbd> <kbd>↑</kbd> <kbd>⇧Space</kbd> <kbd>PgUp</kbd> | previous slide |
| <kbd>Home</kbd> / <kbd>End</kbd> | first / last slide |

Scrolling and swiping work too — slides snap.

## The running order

| # | Slide | Beat |
|---|---|---|
| 1 | Title | — |
| 2 | The stake | what x402 removed |
| 3 | **Act 1 — the disaster** | agent holds the wallet, $5,000 gone |
| 4 | The thesis | "financially inert" |
| 5 | **Act 2 — refused** | same attack, behind the guard |
| 6 | The one edge | before/after architecture |
| 7 | Three properties | custody, catalog, fail closed |
| 8 | Act 3 — not a blocklist | three outcomes + the checks array |
| 9 | Control plane / data plane | the disarm question |
| 10 | The ledger | tamper-evident, anchored |
| 11 | **The closer** | policy proposes its own amendment |
| 12 | The arc | flexibility vs security |
| 13 | The parallel | SQL injection → prompt injection |
| 14 | What's real and what isn't | the honesty slide |
| 15 | Close | every agent sits behind this |

Slide 3 animates the wallet draining once, when it comes into view. It respects
`prefers-reduced-motion`.

## Notes

- No build step, no dependencies, no network. One file, works offline — which
  is the point, on conference wifi.
- Dark by design: it's meant for a projector in a dark room, so it commits to
  one theme rather than following the OS.
- The narration, timings and Q&A prep live in [`../DEMO.md`](../DEMO.md).
  This deck is the visual half; that file is what you say over it.
