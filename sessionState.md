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

### Theme Editor Infrastructure — IN PROGRESS

**Status:** Building foundational infrastructure for AI-powered theme editor

**Completed previously (v4.0.0):**
- JSON Theme Architecture deployed to production
- Theme Manager utility (`helpers/theme_manager.py`)
- Security audit passed (Semgrep, Gitleaks, Bandit)

**Known bugs from Slack:**
- Technical indicators checkboxes broken on prod (functional, not styling)
- Button colors need fixing (Analyze too dark, Clear Comparison)

**Completed this session:**
- Theme preview mini-app component (`wwwroot/js/themePreview.js`) - 500+ lines
  - Self-contained renderer showing header, chart, tiles, buttons, effects
  - Canvas-based chart with line + SMA drawing
  - Scanlines, rain, vignette, CRT flicker effects
  - Accepts theme JSON, renders live preview
- Theme preview demo page (`wwwroot/theme-preview.html`)
  - Test harness at /theme-preview.html
  - Load/switch between built-in themes (light/dark/neon-noir)
  - Paste custom JSON and apply
- Theme inheritance in ThemeLoader.js
  - `extends` property for theme JSON (e.g., `"extends": "dark"`)
  - `mergeThemes()` deep merges base + child
  - Circular inheritance detection
  - `applyThemeJson()` method for editor/preview use

**Theme Editor Architecture (bridges before rafts):**
1. [x] Theme inheritance in ThemeLoader
2. [x] Preview component
3. [ ] Python theme generation service (Claude API)
4. [ ] Editor UI (prompt input + refinement)
5. [ ] localStorage persistence
6. [ ] Azure upload/share

**Patrick's decisions:**
- Python OK for AI service (but research best practices)
- Use existing Azure Blob for storage
- Always Key Vault for secrets
- Build full mini-app preview

**Key URLs:**
- Production: https://psfordtaurus.com
- Themes: https://stockanalyzerblob.z13.web.core.windows.net/themes/

**Say "night!"** at end of session to save state.
