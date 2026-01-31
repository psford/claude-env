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
| Slack | OK | `python helpers/slack_bot.py start` |
| Production | OK | https://psfordtaurus.com v3.0.3 |

---

## Quick Start

```powershell
# Install git hooks (after clone)
./scripts/install-hooks.sh

# Start Slack
python helpers/slack_bot.py start

# Run .NET app
cd projects/stock-analyzer
dotnet run --project src/StockAnalyzer.Api
# Visit http://localhost:5000
```

---

## Where We Left Off

**Last session (01/29/2026):**
- Fixed Slack acknowledger infinite retry bug on `message_not_found` errors
- Built bulk-mark-eodhd-complete endpoint (server + client)
- Added PURGE button to Boris crawler UI
- Automated purge: crawler auto-runs bulk mark on START before fetching gaps
- Started planning PRICE table optimization (7M+ rows in Azure SQL Basic 5 DTU) but stopped before completing the plan

**Uncommitted work:** All of the above is committed in this session's closing commit.

**Pending from Slack (unread):**
- Privacy page is busted (Slack #153)
- Slack listener needs to be a standalone Windows service (Slack #154)
- TOP PRIORITY: Stage environment in Azure — same DBs/endpoints but separate from prod, with ability to rotate stage→prod (Slack #155)
- News sentiment analyzer rebuild — MSFT moved 6% and analyzer couldn't explain why (Slack #156)
- Review ed3d-plugins GitHub page for methodology comparison (Slack #152)

**Say "night!"** at end of session to save state.
