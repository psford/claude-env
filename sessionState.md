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

## NEXT SESSION: Sentiment Filtering Bug Investigation

**Problem:** Headlines with mismatched sentiment still getting through the filter.

**Example:** Tesla +6.45% move showing headline "Tesla (TSLA) Stock Dips While Market Gains: Key Facts"
- "Dips" = negative keyword (should be detected)
- +6.45% = positive price move
- Should have been filtered out (score < 25) but wasn't

**To investigate:**
1. Debug `SentimentAnalyzer.Analyze()` with this exact headline
2. Check if "Dips" is being matched (case sensitivity, word boundaries)
3. Check if "Gains" is counteracting "Dips" in the score calculation
4. Review the scoring threshold (25) - may be too lenient
5. Consider requiring stricter matching for clear sentiment words

**Files to review:**
- `src/StockAnalyzer.Core/Services/SentimentAnalyzer.cs` - keyword matching logic
- `src/StockAnalyzer.Core/Services/NewsService.cs:125` - filter threshold (matchScore > 25)

**Uncommitted changes on develop:**
- NewsService.cs - Removed middle fallback tier (unrelated company news)
- TECHNICAL_SPEC.md - Updated fallback cascade documentation
- These fix the "Curaleaf Holdings showing for Tesla" bug but NOT the sentiment mismatch bug above

---

## Current State (01/23/2026 ~2:10 AM EST)

**Branch status:** develop synced with main after v2.17 deploy
**Production:** v2.17 at https://psfordtaurus.com

**Session accomplishments:**
1. Fixed production timeout (85s → 252ms for significant moves)
2. Parallelized news fetching with SemaphoreSlim (PR #46)
3. Added IMemoryCache for significant moves (PR #47)
4. **v2.17:** Decoupled news from chart load entirely (PR #48)
   - New `/api/stock/{ticker}/news/move` endpoint for lazy loading
   - Frontend fetches news on marker hover
   - Chart loads instantly, news loads on demand

**Roadmap items added (per user request):**
- Server-side watchlists with zero-knowledge encrypted sync
- News caching service to feed sentiment analyzer
- Anonymous API monitoring to pre-cache popular stocks

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
