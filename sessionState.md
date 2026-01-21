# Session State - Last Updated 01/20/2026

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
| Production | ✅ | https://psfordtaurus.com (v2.9) |

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
│   └── check_links.py           # Validate doc links
│
├── projects/stock-analyzer/     # .NET Stock Analyzer
│   ├── docs/                    # FUNCTIONAL_SPEC, TECHNICAL_SPEC
│   ├── ROADMAP.md
│   └── src/StockAnalyzer.Api/   # Web API + frontend
│
└── archive/                     # Historical files
```

---

## Current State (01/20/2026)

**Develop branch:** CA2000 fixes uncommitted (ready to commit)
**Main branch:** v2.9 deployed via PR #25

**Uncommitted changes:**
- `ImageProcessingService.cs` - SessionOptions `using`
- `NewsService.cs` - HttpRequestMessage/HttpResponseMessage `using`
- `NewsServiceTests.cs` - Factory pattern + `using` declarations
- `MarketauxServiceTests.cs` - Factory pattern + `using` declarations
- `AggregatedNewsServiceTests.cs` - Factory pattern

**New file:** `lessonsLearned.md` - POC insights for work presentation

---

## Pending Tasks

**From Slack (priority order):**
1. **News service broken** - #99 reports news not working
2. **Status page mobile CSS** - #101 CSS broken on mobile
3. **Favicon transparent bg** - #105 white bg instead of transparent
4. **iPhone tab bar scroll** - Works in Playwright, not on real iPhone

**From whileYouWereAway.md:**
- Cloudflare IP allowlist (security)
- Favicon from bird image
- Image ML quality control
- CI dashboard
- Brinson Attribution Analysis (major)

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
```

**Say "night!"** at end of session to save state.
