# Session State - Last Updated 01/18/2026 (01:40 AM)

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
- **CI/CD:** GitHub Actions + Jenkins

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
│   │   ├── FUNCTIONAL_SPEC.md   # v2.0
│   │   ├── TECHNICAL_SPEC.md    # v1.18
│   │   ├── CI_CD_SECURITY_PLAN.md
│   │   └── DOTNET_SECURITY_EVALUATION.md
│   ├── ROADMAP.md
│   └── src/
│       ├── StockAnalyzer.Api/   # Web API + frontend
│       │   └── wwwroot/
│       │       ├── index.html
│       │       ├── status.html  # Health dashboard
│       │       └── docs.html    # Documentation viewer
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
- Documentation page with search, TOC, architecture diagrams
- Health monitoring dashboard (/status.html)
- Watchlist feature with sidebar UI, 8 API endpoints, JSON persistence
- **NEW:** Combined Watchlist View with portfolio aggregation, ±5% markers, benchmark comparison

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

## Today's Session Summary (01/17-18/2026)

**Combined Watchlist View (Latest):**
- Portfolio aggregation with equal/shares/dollars weighting modes
- ±5% significant move markers with toggle
- Wikipedia-style hover cards showing market news
- Cat/dog image toggle for hover cards
- Benchmark comparison (SPY/QQQ)
- Holdings editor modal
- FUNCTIONAL_SPEC.md v2.0 with FR-015 (17 requirements)
- TECHNICAL_SPEC.md v1.18 with full documentation
- Commits: 7b64390, 7eac650

**Dependabot PRs Merged:**
- PR #1: actions/setup-dotnet v4 → v5
- PR #2: github/codeql-action v3 → v4
- PR #3: actions/checkout v4 → v6
- PR #4: 10 NuGet packages (dotnet-minor group)

**CodeQL Fix:**
- Added actions:read and pull-requests:read permissions to codeql.yml
- Discovered CodeQL requires GHAS for private repos
- CodeQL configured as non-blocking (PRs can merge when build-and-test passes)

**Next Session:**
- Azure cloud deployment planning for Stock Analyzer
- User switching from PowerShell terminal to VS Code

**Previous Session Highlights:**
- Watchlist feature with 8 CRUD API endpoints
- Health monitoring dashboard (/status.html)
- Async Slack bot (slack_bot.py)
- .NET security analyzers (SecurityCodeScan, NetAnalyzers, Roslynator)

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

**Say "night!"** at end of session to save state.
