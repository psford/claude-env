# While You Were Away

Scratchpad for quick notes and pending tasks.

**For feature requests:** Add to [ROADMAP.md](projects/stock-analyzer/ROADMAP.md) instead.

---

## Pending Tasks

### Bugs / Immediate Fixes
- [x] ~~**Hide cat/dog toggle until markers checked**~~ — cat/dog image toggle hidden until "show markers" checkbox is checked (PR #108, deployed 02/02)
- [ ] **Wikipedia fallback for company bios** — default to Wikipedia when financial API returns blank bio (e.g. BA is blank) (Slack #177)

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
- [ ] **Movable/resizable dashboard tiles** — turn sections (search, bio, metrics, etc.) into draggable tiles (1x1, 1x2, 2x2, etc.), config saved in localStorage (Slack #169)
- [ ] **FOUC mitigation** — prevent Flash of Unstyled Content on page load (Slack #175)
- [ ] **PRICE table partitioning strategy** — table could reach 1B+ rows, need to plan partitioning now (Slack #149, #150)
- [ ] **Add listing date to SecurityMaster** — enables per-security coverage metrics (expected trading days from listing to present)

- [ ] **Cloudflare rate-limiting/timeout audit** — audit all admin endpoints for Cloudflare 524 timeouts, determine maintenance bypass strategy (direct origin access, Cloudflare API rules, or both)

### Research
- [ ] Review ed3d-plugins: https://github.com/ed3dai/ed3d-plugins — evaluate methodology, dependencies, comparison to current approach (Slack #152)

### UI/Design
- [ ] **Vaporwave theme + UI prototypes** — new theme option (light/dark/vaporwave), plus 10 UI prototype mockups on a viewable page (Slack #171)

### Other Projects
- [ ] **Remake Logo Writer** — new project, separate from stock analyzer (Slack #135, #136)

### Completed (02/02/2026)
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
