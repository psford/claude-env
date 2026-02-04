# While You Were Away

Scratchpad for quick notes and pending tasks.

**For feature requests:** Add to [ROADMAP.md](projects/stock-analyzer/ROADMAP.md) instead.

---

## Pending Tasks

### Bugs / Immediate Fixes
- [x] ~~**Hide cat/dog toggle until markers checked**~~ — cat/dog image toggle hidden until "show markers" checkbox is checked (PR #108, deployed 02/02)
- [x] ~~**Wikipedia fallback for company bios**~~ — CompanyBio table in `data` schema caches descriptions from Wikipedia/providers. First lookup fetches externally + stores in Azure SQL; subsequent lookups served from DB. EF Core migration `AddCompanyBio`. (Slack #177)

### High Priority
- [x] ~~Real-time stats during crawling~~ — Live Price Records + universe cards during crawl (PR #105, deployed)
- [x] ~~Custom date range search fields~~ — From/to date inputs, keyboard nav, cache-busting, Clear button (PR #105, deployed)
- [ ] **Stage environment in Azure** — same DBs/endpoints, NOT psfordtaurus.com, ability to test then rotate to prod near-instantly (Slack #155) — **LONG-TERM: requires S1 Standard ~$70/mo for deployment slots, not justified for current traffic**
- [x] ~~Rebuild news sentiment analyzer~~ — Fixed relevance scoring, sentiment enrichment, fallback cascade (PR #104, deployed)
- [x] ~~News API look forward~~ — Extended date window to date+3 days (PR #104, deployed)
- [ ] **Index master & constituent tables** — create tables for tracking index membership (Slack #137, #138)
- [ ] **Background price history for watchlist stocks** — when user adds stock to watchlist, track it in DB going forward (Slack #139, #140)
- [ ] **Data visualizer dashboard for price coverage** — visual dashboard showing coverage state (Slack #141, #142)
- [ ] **Data loader for indexes** — search for Russell 1000, DJI, etc. and load constituent data; needs refinement before dev (Slack #143)
- [ ] **Compact Boris data loader** — small always-running app to populate production price table using EODHD 75K API calls/day budget, with cool data visualization (Slack #144)
- [ ] **FX rate table** — foreign exchange rate table (Slack #165)
- [x] ~~Movable/resizable dashboard tiles~~ — GridStack.js v12 tile dashboard with physics engine, coupled resize, layout persistence (PR #110, deployed 02/02)
- [x] ~~FOUC mitigation~~ — dark mode blocking script in `<head>` prevents flash (PR #110, deployed 02/02)
- [ ] **PRICE table partitioning strategy** — table could reach 1B+ rows, need to plan partitioning now (Slack #149, #150)
- [ ] **Add listing date to SecurityMaster** — enables per-security coverage metrics (expected trading days from listing to present)

- [ ] **Cloudflare rate-limiting/timeout audit** — audit all admin endpoints for Cloudflare 524 timeouts, determine maintenance bypass strategy (direct origin access, Cloudflare API rules, or both)

### UI Enhancements
- [x] ~~Hover-over tooltips for technical indicators~~ — title attributes on all 7 indicator checkboxes (PR #112, deployed 02/02)
- [x] ~~Wikipedia rate limiting + CWE-117 fix~~ — SemaphoreSlim rate limiter, LogSanitizer.Sanitize() on all log params, blocking pre-commit hook (PR #112, deployed 02/02)

### Research
- [ ] Review ed3d-plugins: https://github.com/ed3dai/ed3d-plugins — evaluate methodology, dependencies, comparison to current approach (Slack #152)

### UI/Design
- [x] ~~**Neon Noir theme (Vaporwave)** — framework-first theming system: CSS variables for colors, structure, charts; JS reads from CSS; square corners, glowing text, scanlines, rain, diamond markers, cyan/magenta price colors (02/03)~~
- [ ] **Hover-news cards theming** — significant move marker hover cards (Wikipedia-style popups) need refactoring to inherit from theme system like charts.js does. Currently hardcoded styles, should use CSS variables for bg, text, border, shadows, accent colors.

### Other Projects
- [ ] **Remake Logo Writer** — new project, separate from stock analyzer (Slack #135, #136)

### Completed (02/03/2026)
- [x] ~~Watchlist tile with horizontal expansion~~ — sidebar→tile conversion, star toggle, neighbor expansion on close/reopen (PR #113, deployed)

### Completed (02/02/2026)
- [x] ~~Tile dashboard with physics engine (v3.1.0)~~ — 6 draggable/resizable tiles, coupled resize, snap audio, layout persistence, reset, dark mode FOUC fix (PR #110, deployed)
- [x] ~~Click-and-drag performance measurement~~ — dragMeasure.js: left-drag measure bubble, right-drag zoom, scroll wheel zoom, scroll-out data extension (PR #108, deployed)
- [x] ~~Cat/dog toggle hidden until markers checked~~ — both individual and combined views (PR #108, deployed)
- [x] ~~Markers default off~~ — show-markers checkbox starts unchecked (PR #108, deployed)
- [x] ~~Search keyboard nav fix~~ — Enter on highlighted dropdown item now loads stock (PR #108, deployed)
- [x] ~~Chart block reorder~~ — chart moved above bio/metrics in results section (PR #108, deployed)

### Completed (02/01/2026)
- [x] ~~Date range UI redesign with flatpickr~~ — End/start date labels, flatpickr calendar pickers, flexible date parsing (PR #107, deployed)
- [x] ~~Bicep sync + deploy warmup~~ — Fixed stale Bicep (F1→B1), added drift detection preflight step, added cache warmup step (PR #108)

### Completed (01/31/2026)
- [x] ~~PRICE table optimization~~ — Eliminated all full-table scans (PRs #96, #97, deployed)
- [x] ~~Stock splits in charts~~ — AdjustForSplits() using AdjustedClose ratio (PR #98, deployed)
- [x] ~~Slack listener as Windows service~~ — NSSM services installed, auto-start + failure recovery
- [x] ~~Privacy page busted~~ — Copied PRIVACY_POLICY.md to root docs/ for GitHub Pages, added .gitignore exception
- [x] ~~EODHD not on sources page~~ — Added EODHD as first data source in about.html
- [x] ~~Heatmap not updating during crawling~~ — Removed API refresh during crawl (was overwriting local cells with 30-min cached stale data), added local cell creation for new year/score combos
- [x] ~~Boris coverage report busted~~ — Removed misleading "Date Coverage" metric, renamed to "Record Completeness" with context

---

## Blog Ideas

- [ ] "LLMs are border collies" - analogy for working with AI assistants (Slack #88-89)

---

## Version History

| Date | Change |
|------|--------|
| 02/02/2026 | Deployed drag-measure tool, cat/dog toggle fix, markers default off, search Enter fix, chart reorder. Updated APP_EXPLANATION.md, ROADMAP.md, all specs. |
| 02/01/2026 | Synced Slack inbox: added FX rate table, dashboard tiles, vaporwave theme, cat/dog toggle fix, FOUC mitigation, compact Boris loader. Fixed #144 reference (was index loader, is Boris loader). Added 02/01 completions. |
| 01/31/2026 | Added new Slack items: index tables, watchlist tracking, coverage dashboard, data loader, PRICE partitioning, Boris coverage bug, Logo Writer project |
| 01/31/2026 | Completed PRICE optimization, stock split fix, Slack as Windows services. Added EODHD sources + news look-forward tasks |
| 01/25/2026 | Fixed dark mode code block highlight issue (#120), cleaned up all pending bugs |
| 01/21/2026 | Moved feature requests to ROADMAP.md (favicon, staging, Cloudflare IP, CI dashboard, Brinson) |
| 01/21/2026 | Synced with Slack inbox, reorganized by priority |
| 01/20/2026 | Pruned completed items and archived section to reduce context |
| 01/19/2026 | Cleaned up: Removed obsolete App Service quota check, marked favicon as done |
