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
| Production | OK | https://psfordtaurus.com v4.0.0 |
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

**Last session (02/04/2026):**

### JSON-Based Theming System with Azure Hosting — COMPLETE

**Status:** PR #115 merged and deployed. v4.0.0 live at https://psfordtaurus.com

**What's done:**
- **JSON Theme Architecture** - Themes defined in JSON, not CSS classes
  - ThemeLoader module (`wwwroot/js/themeLoader.js`) - 471 lines
  - Fetches from Azure first, falls back to local `/themes/`
  - CSP updated to allow `stockanalyzerblob.z13.web.core.windows.net`
  - 94+ CSS variables per theme

- **Theme Files** on Azure Blob Storage:
  - `manifest.json` - theme registry
  - `light.json`, `dark.json` - standard themes
  - `neon-noir.json` - CRT effects (scanlines, bloom, rain, vignette)

- **Theme Manager Utility** (`helpers/theme_manager.py`):
  - `list` - show available themes
  - `preview <id>` - show colors/effects
  - `create <new_id> --from <base>` - create from template
  - `validate` - check JSON structure
  - `deploy <id>` - validate + upload to Azure
  - `upload --all` - upload all themes

- **Fixed watchlist.js** - replaced hard-coded colors with CSS variables

- **Security Audit** - ran aggressive scans:
  - Semgrep: 0 findings (95 rules on C#/JS)
  - dotnet vulnerable: 0 CVEs (all 3 projects)
  - Bandit: 0 medium/high (39 low informational)
  - Gitleaks: 10 false positives only

**Key URLs:**
- Production: https://psfordtaurus.com
- Themes: https://stockanalyzerblob.z13.web.core.windows.net/themes/

**Tools installed this session:**
- Semgrep 1.150.0
- Gitleaks 8.30.0
- Bandit 1.9.3

**Pending:**
- None - all work committed and deployed

**Say "night!"** at end of session to save state.
