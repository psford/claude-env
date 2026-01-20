# Session State - Last Updated 01/19/2026 (04:25 AM)

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
- **Repository:** C:\Users\patri\Documents\claudeProjects (develop branch)
- **Branch Guard:** GitHub Actions workflow blocks main→develop merges

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
- **Project:** projects/stock-analyzer (ASP.NET Core minimal API + Tailwind CSS frontend)
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
- **Infrastructure:** Azure App Service (B1) + Azure SQL
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
│
├── .github/                     # GitHub workflows and config
│   ├── workflows/
│   │   ├── azure-deploy.yml     # Production deployment
│   │   ├── branch-guard.yml     # Block main→develop merges
│   │   ├── codeql.yml           # Weekly SAST scans
│   │   ├── docs-deploy.yml      # GitHub Pages docs
│   │   └── dotnet-ci.yml        # Build + test + security scan
│   ├── dependabot.yml           # Auto dependency updates
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS
│
├── helpers/                     # Shared Python scripts
│   ├── slack_bot.py             # Async bot manager (start/stop/status)
│   ├── slack_listener.py        # Receive messages
│   ├── slack_acknowledger.py    # Auto-acknowledge read messages
│   ├── slack_notify.py          # Send messages & reactions
│   ├── ui_test.py               # Playwright UI testing
│   ├── speech_to_text.py        # Whisper transcription
│   └── checkpoint.py            # Session state saves
│
├── projects/
│   └── stock-analyzer/          # .NET Stock Analyzer project
│       ├── .editorconfig        # Analyzer rules (CA5xxx as errors)
│       ├── docs/
│       │   ├── FUNCTIONAL_SPEC.md   # v2.2 (mobile responsiveness)
│       │   ├── TECHNICAL_SPEC.md    # v2.6
│       │   ├── PROJECT_OVERVIEW.md  # Project stats
│       │   ├── SECURITY_OVERVIEW.md # CISO-friendly security doc
│       │   ├── CI_CD_SECURITY_PLAN.md
│       │   └── DOTNET_SECURITY_EVALUATION.md
│       ├── ROADMAP.md
│       ├── tests/
│       │   └── StockAnalyzer.Core.Tests/  # 150 tests
│       └── src/
│           ├── StockAnalyzer.Api/   # Web API + frontend
│           │   └── wwwroot/
│           │       ├── index.html
│           │       ├── status.html  # Health dashboard
│           │       └── docs.html    # Documentation viewer
│           └── StockAnalyzer.Core/  # Business logic
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
- Cat/dog popup thumbnails with ML cropping (YOLOv8)
- Dark mode toggle
- Documentation page with search, TOC, architecture diagrams, Security tab
- Health monitoring dashboard (/status.html)
- Watchlist feature with sidebar UI, 10 API endpoints, localStorage persistence
- Combined Watchlist View with portfolio aggregation, ±5% markers, benchmark comparison
- **Mobile responsive UI** with hamburger menu and slide-in sidebar

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

## Today's Session Summary (01/20/2026)

**v2.8 in Progress:**
- Created About Us page with privacy principles
- Refactored site-wide footer to two-line layout
- Deploying to production via PR #20

**v2.7 Deployed Earlier:**
- Merged PR #19 (mobile responsiveness, workflow consolidation)
- Production live at https://psfordtaurus.com

**Workflow Consolidation:**
- Moved all workflows to repo root `.github/workflows/`
- Fixed: dotnet-ci.yml, azure-deploy.yml, branch-guard.yml
- Reason: GitHub only recognizes `workflow_dispatch` and status checks from repo root

---

## Current State

**Develop branch:** About Us page + footer redesign (commit 2c4d1e8)
**Main branch:** Merging v2.8 now

---

## Next Session Focus

**Brinson Attribution Analysis** - Major feature, starting architecture planning.

**Pending Items from Slack:**
- Favicon from bird image (`slack_downloads/20260119_025039_robin_fat_bird.png`)
- Image ML quality control (reject bad crops)
- CI dashboard

**From ROADMAP:**
- Stats tab for docs page (LOC, classes, tests)
- Container bundle audit (exclude unused files from prod)
- Cold start optimization (defer ImageCacheService prefill)

---

## Quick Start for New Session

**Say "hello!"** to restore context.

Then:
1. Start Slack bot: `python helpers/slack_bot.py start`
2. Check status: `python helpers/slack_bot.py status`
3. Review tasks: Read `whileYouWereAway.md`

To run .NET app:
```powershell
cd projects/stock-analyzer
dotnet run --project src/StockAnalyzer.Api
# Visit http://localhost:5000
# Status dashboard: http://localhost:5000/status.html
```

**Production:** https://psfordtaurus.com

**Say "night!"** at end of session to save state.
