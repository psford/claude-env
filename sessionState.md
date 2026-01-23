# Session State - Last Updated 01/23/2026

Use this file to restore context when starting a new session. Say **"hello!"** to restore state.

---

## User Profile

- **Name:** Patrick (psford)
- **Background:** Financial services business analyst
- **Preferred languages:** Python, TypeScript, HTML, CSS, C# (.NET)

---

## Environment Status

| Component | Status | Notes |
|-----------|--------|-------|
| Git | ✅ | psford <patrick@psford.com>, SSH auth |
| GitHub | ✅ | Branch protection, CI/CD via Actions |
| Python | ✅ | 3.10.11 |
| .NET | ✅ | .NET 8 |
| Slack | ✅ | `python helpers/slack_bot.py start` |
| Production | ✅ | https://psfordtaurus.com |

---

## Project Structure

```
claudeProjects/
├── CLAUDE.md                    # Guidelines (read first!)
├── sessionState.md              # This file
├── claudeLog.md                 # Action log (recent only)
├── whileYouWereAway.md          # Task queue
├── swearJar.json                # Tracks repeated mistakes
│
├── helpers/                     # Python scripts
│   ├── slack_bot.py             # start/stop/status
│   ├── ui_test.py               # Playwright testing
│   ├── responsive_test.py       # Mobile/tablet/desktop
│   ├── test_docs_tabs.py        # Docs page tab verification
│   └── check_links.py           # Validate doc links
│
├── docs/                        # GitHub Pages source (psford.github.io/claudeProjects/)
│   ├── APP_EXPLANATION.md
│   ├── FUNCTIONAL_SPEC.md
│   ├── TECHNICAL_SPEC.md
│   ├── SECURITY_OVERVIEW.md
│   ├── PRIVACY_POLICY.md
│   └── diagrams/*.mmd
│
├── projects/stock-analyzer/     # .NET Stock Analyzer
│   ├── docs/                    # Source specs (sync to /docs for GH Pages)
│   ├── ROADMAP.md
│   └── src/StockAnalyzer.Api/   # Web API + frontend
│
└── archive/                     # Historical files
```

---

## Current State (01/23/2026)

**Branch status:** develop with uncommitted changes for historical price loading
**Production:** v2.18 at https://psfordtaurus.com

**Recent session accomplishments:**
1. Created `data` schema for SecurityMaster and Prices tables
2. Built EODHD API integration for historical price data
3. Created PriceRefreshService background service for daily updates
4. Added admin endpoints: `/status`, `/sync-securities`, `/refresh-date`, `/bulk-load`, `/load-tickers`
5. Synced 29,873 securities from Symbols table to SecurityMaster
6. Loaded 23,012 prices from EODHD bulk API for 2026-01-22
7. Tested per-ticker backfill: AAPL + TSLA = 3,054 historical records (10 years)
8. Total price database: 28,066 records

**Data infrastructure (new):**
- SecurityMaster table: Central security reference with auto-incrementing SecurityAlias
- Prices table: Historical OHLC data optimized for ~1.26M rows
- EODHD API: $19.99/mo for bulk historical data
- BulkInsertAsync: Handles duplicates by checking existing keys before insert

**Sentiment analysis system (completed):**
- Keyword-based analysis with word-boundary matching (regex `\b`)
- VADER integration for ensemble scoring (60% keyword / 40% VADER)
- FinBERT ONNX infrastructure in place (optional ML layer)
- Added missing keywords: "dip", "dips", "slump", "weaken", etc.

**Production URLs:**
- App: https://psfordtaurus.com
- Docs: https://psford.github.io/claudeProjects/

---

## Pending Tasks

**From ROADMAP.md High Priority:**
- Server-side watchlists (zero-knowledge encrypted sync)
- News caching service
- Anonymous API monitoring
- Staging environment
- Brinson Attribution Analysis

**From whileYouWereAway.md:**
- Azure Front Door (Slack #122)
- Symbol tracking for lookups (Slack #124)
- paddleLog refactor (Slack #126)

---

## Quick Start

```powershell
# Start Slack
python helpers/slack_bot.py start

# Run .NET app
cd projects/stock-analyzer
dotnet run --project src/StockAnalyzer.Api
# Visit http://localhost:5000

# Responsive testing
python helpers/responsive_test.py http://localhost:5000/docs.html --prefix docs

# Test docs tabs
python helpers/test_docs_tabs.py http://localhost:5000/docs.html
```

**Say "night!"** at end of session to save state.
