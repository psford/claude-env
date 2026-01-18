# Session State - Last Updated 01/18/2026 (04:10 AM)

Use this file to restore context when starting a new session. Say **"hello!"** to restore state.

---

## User Profile

- **Name:** Patrick (psford)
- **Background:** Financial services business analyst, experience with Matlab, Python, Ruby
- **Preferred languages:** Python, TypeScript, HTML, CSS, C# (.NET)
- **Email:** patrick@psford.com

---

## Environment Status

### Git
- **Status:** Configured and working
- **User:** psford <patrick@psford.com>
- **Repository:** C:\Users\patri\Documents\claudeProjects (master branch)

### GitHub
- **Status:** CONNECTED (SSH auth)
- **Auth:** ED25519 SSH key (~/.ssh/github_ed25519)
- **Branch protection:** Enabled (PR reviews, status checks)
- **CI/CD:** GitHub Actions + Azure deployment

### Python
- **Version:** 3.10.11
- **Core packages:** yfinance, pandas, numpy, slack-sdk, slack-bolt, playwright, openai-whisper, python-dotenv, bandit

### .NET
- **Version:** .NET 8
- **Project:** stock_analyzer_dotnet (ASP.NET Core minimal API + Tailwind CSS frontend)
- **Analyzers:** SecurityCodeScan, NetAnalyzers, Roslynator

### Slack Integration
- **Status:** OPERATIONAL (async bot)
- **Workspace:** psforddigitaldesign.slack.com
- **Channel:** #claude-notifications (C0A8LB49E1M)
- **Start bot:** `python helpers/slack_bot.py start`
- **Check status:** `python helpers/slack_bot.py status`
- **Stop bot:** `python helpers/slack_bot.py stop`

### Production Deployment
- **Status:** LIVE at https://psfordtaurus.com
- **Infrastructure:** Azure Container Instance + Azure SQL
- **CDN/SSL:** Cloudflare (Full SSL mode)
- **Deploy:** GitHub Actions (manual trigger with confirmation)

---

## Project Structure

```
claudeProjects/
├── CLAUDE.md                    # Guidelines
├── sessionState.md              # This file
├── claudeLog.md                 # Action log
├── whileYouWereAway.md          # Task queue
├── .env                         # API keys (gitignored)
├── slack_inbox.json             # Slack messages
│
├── .github/
│   ├── workflows/
│   │   ├── dotnet-ci.yml        # Build + test + security scan
│   │   ├── azure-deploy.yml     # Production deployment
│   │   └── codeql.yml           # Weekly SAST scans
│   ├── dependabot.yml           # Auto dependency updates
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS
│
├── helpers/                     # Reusable Python scripts
│   ├── slack_bot.py             # Async bot manager (start/stop/status)
│   ├── slack_listener.py        # Receive messages
│   ├── slack_acknowledger.py    # Auto-acknowledge read messages
│   ├── slack_notify.py          # Send messages & reactions
│   ├── ui_test.py               # Playwright UI testing
│   ├── speech_to_text.py        # Whisper transcription
│   └── checkpoint.py            # Session state saves
│
├── stock_analyzer_dotnet/       # Active .NET project
│   ├── .editorconfig            # Analyzer rules (CA5xxx as errors)
│   ├── docs/
│   │   ├── FUNCTIONAL_SPEC.md   # v2.1
│   │   ├── TECHNICAL_SPEC.md    # v1.18
│   │   ├── SECURITY_OVERVIEW.md # CISO-friendly security doc
│   │   ├── CI_CD_SECURITY_PLAN.md
│   │   └── DOTNET_SECURITY_EVALUATION.md
│   ├── ROADMAP.md
│   └── src/
│       ├── StockAnalyzer.Api/   # Web API + frontend
│       │   └── wwwroot/
│       │       ├── index.html
│       │       ├── status.html  # Health dashboard
│       │       └── docs.html    # Documentation viewer (with Security tab)
│       └── StockAnalyzer.Core/  # Business logic
│
└── archive/                     # Archived projects
```

---

## .NET Dashboard Features

- REST API with stock data endpoints
- Interactive Plotly charts (candlestick, line)
- Moving averages (SMA 20, 50, 200)
- Technical indicators: RSI, MACD, Bollinger Bands
- Stock comparison mode
- Significant move markers with hover cards
- Cat/dog popup thumbnails
- Dark mode toggle
- Documentation page with search, TOC, architecture diagrams, Security tab
- Health monitoring dashboard (/status.html)
- Watchlist feature with sidebar UI, 8 API endpoints, JSON persistence
- Combined Watchlist View with portfolio aggregation, ±5% markers, benchmark comparison

---

## Security Tools

| Tool | Type | Integration |
|------|------|-------------|
| SecurityCodeScan | SAST | Build-time |
| NetAnalyzers | SAST | Build-time |
| Roslynator | Code quality | Build-time |
| CodeQL | SAST | GitHub Actions (weekly) |
| OWASP Dep Check | SCA | GitHub Actions |
| Dependabot | SCA | GitHub (auto-PRs) |
| Bandit | Python SAST | Pre-commit |
| detect-secrets | Secrets | Pre-commit |

---

## Today's Session Summary (01/18/2026)

**Azure Production Deployment Fixed:**
- Fixed SQL connection string (username was stockadmin, actual is sqladmin)
- Added AllowAzureServices SQL firewall rule (0.0.0.0/0.0.0.0) to avoid per-IP rules
- Updated Cloudflare DNS to track new ACI IP (48.200.21.106)
- Site live at https://psfordtaurus.com

**CISO Security Document:**
- Created SECURITY_OVERVIEW.md with executive summary, risk profile, OWASP Top 10 mapping
- Added Security tab to docs.html
- Updated FUNCTIONAL_SPEC.md to v2.1

**Slack Integration Fix:**
- Fixed slack_notify.py --react command (channel ID lookup table added)

**Roadmap Updates from Slack:**
- Added: Mobile responsiveness (High Priority)
- Added: CISO security document (completed)
- Added: Stats tab for docs
- Added: Container bundle audit
- Added: VNet + Private Endpoint option

---

## Next Session Focus

**Mobile Responsiveness:**
- Site looks rough on mobile/tablet
- Prioritize mobile-friendly layout
- May need UI testing enhancements

**Other Pending Items:**
- Stats tab for docs page (LOC, classes, tests)
- Larger hover card images (square aspect ratio)
- Container bundle audit (exclude unused files from prod)
- Mermaid chart verification

---

## Quick Start for New Session

**Say "hello!"** to restore context.

Then:
1. Start Slack bot: `python helpers/slack_bot.py start`
2. Check status: `python helpers/slack_bot.py status`
3. Review tasks: Read `whileYouWereAway.md`

To run .NET app:
```powershell
cd stock_analyzer_dotnet
dotnet run --project src/StockAnalyzer.Api
# Visit http://localhost:5000
# Status dashboard: http://localhost:5000/status.html
```

**Production:** https://psfordtaurus.com

**Say "night!"** at end of session to save state.
