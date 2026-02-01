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
| Production | OK | https://psfordtaurus.com v3.0.3 |
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

**Last session (02/01/2026):**

Completed work:
- **Boris dashboard redesign (PR #101, merged+deployed):** 3-tier metric layout, session intelligence, freshness indicators, fixed critical Card 3 binding bug
- **Fix stale Price Records (PR #102, merged+deployed):** Replaced CoverageSummary-derived totalRecords with `sys.dm_db_partition_stats` for real-time count (zero DTU). Production now shows 19.3M instead of stale 5.2M
- **Chart loading performance optimization (PR #103, merged+deployed):** 6 optimizations:
  1. Combined `/chart-data` endpoint (1 request instead of 2)
  2. Cache coalescing via ConcurrentDictionary (stampede prevention)
  3. HttpClient timeouts (15s/10s vs default 100s)
  4. Plotly.react for incremental re-renders
  5. DB connection pool warmup (DbWarmupService + Min Pool Size=2)
  6. Eliminated chart double-render on significant move arrival
- **EODHD-loader rebuild guard hook:** PostToolUse hook + CLAUDE.md D7 protocol to prevent committing eodhd-loader changes without rebuilding

**Tomorrow's priority:**
- **News service not working well** — Patrick flagged this as next task
- Check whileYouWereAway.md for other pending items

**Say "night!"** at end of session to save state.
