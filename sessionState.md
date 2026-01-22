# Session State - Last Updated 01/22/2026

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

## Current State (01/22/2026)

**Develop branch:** Synced with main
**Main branch:** Production with v2.12 client-side instant search

**Recent work (today):**
- Deployed client-side instant search (PR #39)
  - ~30K symbols loaded to browser at page load (~315KB gzipped)
  - Sub-millisecond search latency
  - 5-second debounced server fallback for unknown symbols
  - symbolSearch.js module
- Updated documentation (PR #40)
  - TECHNICAL_SPEC.md → v2.12
  - FUNCTIONAL_SPEC.md → v2.4
  - ROADMAP.md updated with completed features

**Production URLs:**
- App: https://psfordtaurus.com
- Docs: https://psford.github.io/claudeProjects/

---

## Pending Tasks

**From whileYouWereAway.md:**
- Persistent image cache (plan exists at ~/.claude/plans/curious-puzzling-crescent.md)
- Tablet responsive layout fix (~1100-1200px width issues)
- Cloudflare IP allowlist (security)
- CI dashboard
- Brinson Attribution Analysis (major feature - needs planning)

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
