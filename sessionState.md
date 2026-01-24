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

**Last session (01/23/2026):** Cleaned up stale plan files and simplified sessionState.md per prior agreement. Added "Plan and todo hygiene" section to CLAUDE.md to prevent stale state. Security Master/Prices feature complete on `feature/security-master-prices` branch.

**Say "night!"** at end of session to save state.
