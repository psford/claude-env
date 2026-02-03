# Session State

Say **"hello!"** to restore context from CLAUDE.md and this file.

---

## Environment

| Component | Status | Notes |
|-----------|--------|-------|
| Git | OK | psford <patrick@psford.com>, SSH auth |
| GitHub | OK | Branch protection, CI/CD via Actions |
| GitHub App | OK | `claude-code-bot` - commit-only, no merge/deploy |
| Python | OK | 3.10.11 |
| .NET | OK | .NET 8 |
| Slack | OK | Windows services (SlackListener + SlackAcknowledger), auto-start on boot |
| Production | Deploying | https://psfordtaurus.com v3.0.5 — deploy triggered 02/02/2026 |
| NSSM | OK | Installed via winget, manages Slack services |

---

## Quick Start

```powershell
# Install git hooks (after clone)
./scripts/install-hooks.sh

# Slack services are now Windows services - auto-start on boot
# To manage: nssm status/restart/stop SlackListener (or SlackAcknowledger)
# To reinstall: Run helpers/install_slack_services.ps1 as Administrator

# Run .NET app
cd projects/stock-analyzer
dotnet run --project src/StockAnalyzer.Api
# Visit http://localhost:5000
```

---

## Where We Left Off

**Last session (02/02/2026, continued):**

### Tile Dashboard Prototype — Phase 1 Complete, Awaiting User Testing

**Status:** Phase 1 prototype COMPLETE with physics engine. All 37 functional tests + 11 performance tests passing. Awaiting Patrick's manual testing for "feel" evaluation.

**What's done (Phase 1 — all complete):**
- Prototype at `wwwroot/prototypes/tile-dashboard.html` — 7 draggable/resizable/closeable tiles on GridStack.js v12
- 12-column grid layout (chart 9col + watchlist 3col side-by-side, etc.)
- Fixed GridStack v12 CSS issues (`position: absolute !important` overrides, `columnOpts` syntax)
- Close/reopen tiles via panel dropdown with checkboxes
- Dark mode toggle with Plotly chart re-theming
- Layout persistence via localStorage with version-based invalidation (version 3)
- Collapsible search bar (stays at top, never removable)
- Subtle dot grid background showing snap points (glow blue during drag)

**Physics Engine (complete):**
- Spring-based CSS transitions: `cubic-bezier(0.25, 1.1, 0.5, 1)` for neighbor reflow (10% overshoot)
- Lift effect on drag: scale 1.025, enhanced shadow, border glow, reduced opacity
- Magnetic attraction during drag: quadratic easing toward placeholder (50px threshold, 0.35 strength)
- Snap settle animation on drop: `snapSettle` keyframes with scale overshoot + blue glow ring (400ms)
- Placeholder entrance animation (200ms fade-in + scale)
- Optional snap audio: Web Audio API, two-oscillator synthesis (1200Hz tick + 300Hz thud), off by default
- Per-tile lock buttons: toggle lock/unlock via GridStack `noMove`/`noResize`/`locked`
- Haptic feedback via `navigator.vibrate` on mobile
- Cached placeholder reference during drag (performance optimization)

**Performance verified (mobile, 4x CPU throttle):**
- Page load: 5.6s (DOMContentLoaded: 575ms)
- Zero long tasks during idle — no continuous polling
- Touch drag completes in <1s
- JS heap: 19.6MB — lightweight
- GPU-friendly CSS: `transform`/`opacity` for animations
- Mobile single-column works correctly at 390x844

**Test suites:**
- `scratchpad/test_tile_prototype.py` — 37 tests (functional)
- `scratchpad/test_tile_perf.py` — 11 tests (performance/mobile)

**What needs user evaluation:**
- Does the drag feel "magnetic" and "fun"?
- Is the spring settle satisfying?
- Snap audio sound quality (when enabled)
- Overall polish and feel

**Next steps (Phase 2 — production integration):**
- Plan file: `~/.claude/plans/dazzling-petting-fern.md`
- 10-step integration: add GridStack locally, create tileDashboard.js module, restructure results HTML, etc.
- Only proceed after Patrick approves prototype feel

**Unread Slack messages:** #3-#7 in slack_inbox.json (tile sizing, MarketAux API limits, lockable positions)

**Production:** v3.0.5 deployed at https://psfordtaurus.com (PR #108 + #109)

**Say "night!"** at end of session to save state.
