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

**Last session (02/02/2026):**

Completed work:
- **Click-and-drag performance measurement (PR #108, deploying):** New `dragMeasure.js` module (695 lines) — left-click drag shows floating bubble with % return / $ change / date range updating in real time. Right-click drag zooms to selection. Scroll wheel zooms with rAF throttling. Double-click resets. Scrolling past data bounds fetches additional history (right edge clamped to present). Works on both stock charts and portfolio charts.
- **Search keyboard nav fix:** Enter on highlighted dropdown item now triggers analyzeStock()
- **Markers default off:** Show Markers checkbox starts unchecked
- **Cat/dog toggle visibility:** Hidden until markers checkbox is checked (both individual and combined views)
- **Chart block reorder:** Chart moved above bio/metrics in results section
- **Specs updated:** TECHNICAL_SPEC.md (dragMeasure.js module docs), FUNCTIONAL_SPEC.md (FR-016), APP_EXPLANATION.md (v1.1), ROADMAP.md (new Chart Interaction section)

**Deploy status:** PR #108 merged, Azure deploy workflow running. Includes Bicep sync + warmup step from prior commit.

**Plan file:** `~/.claude/plans/dazzling-petting-fern.md` — Phase 1 complete, delete after deploy confirmed.

**Say "night!"** at end of session to save state.
