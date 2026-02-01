# While You Were Away

Scratchpad for quick notes and pending tasks.

**For feature requests:** Add to [ROADMAP.md](projects/stock-analyzer/ROADMAP.md) instead.

---

## Pending Tasks

### Bugs / Immediate Fixes
- [ ] Privacy page is busted (Slack #153)
- [ ] EODHD not listed on sources page (Slack #157)
- [ ] **Heatmap not updating during crawling** — loaded millions of records but heatmap shows no change; fuzzing may be masking progress (Slack #163, #164)
- [ ] **Boris coverage report busted** — shows 99-100% coverage but 0.6% actual record density; numbers don't add up (Slack #147, #148)

### High Priority
- [ ] **Real-time stats during crawling** — update price record count periodically while crawler runs, not just at session start (Slack #161)
- [ ] **Custom date range search fields** — start/end date inputs with standard investment periods (1d, MTD, YTD, 1y-10y, 15y, 20y, 30y, since-inception) and flexible date format input (Slack #162)
- [ ] **Stage environment in Azure** — same DBs/endpoints, NOT psfordtaurus.com, ability to test then rotate to prod near-instantly (Slack #155)
- [ ] **Rebuild news sentiment analyzer** — MSFT moved 6% in a day and analyzer couldn't figure out why (Slack #156)
- [ ] **News API look forward** — search for news a few days AFTER a significant price move, not just on the day (Slack #160)
- [ ] **Index master & constituent tables** — create tables for tracking index membership (Slack #137, #138)
- [ ] **Background price history for watchlist stocks** — when user adds stock to watchlist, track it in DB going forward (Slack #139, #140)
- [ ] **Data visualizer dashboard for price coverage** — visual dashboard showing coverage state (Slack #141, #142)
- [ ] **Data loader for indexes** — search for Russell 1000, DJI, etc. and load constituent data; needs refinement before dev (Slack #143, #144)
- [ ] **PRICE table partitioning strategy** — table could reach 1B+ rows, need to plan partitioning now (Slack #149, #150)
- [ ] **Add listing date to SecurityMaster** — enables per-security coverage metrics (expected trading days from listing to present)

### Research
- [ ] Review ed3d-plugins: https://github.com/ed3dai/ed3d-plugins — evaluate methodology, dependencies, comparison to current approach (Slack #152)

### Other Projects
- [ ] **Remake Logo Writer** — new project, separate from stock analyzer (Slack #135, #136)

### Completed (01/31/2026)
- [x] ~~PRICE table optimization~~ — Eliminated all full-table scans (PRs #96, #97, deployed)
- [x] ~~Stock splits in charts~~ — AdjustForSplits() using AdjustedClose ratio (PR #98, deployed)
- [x] ~~Slack listener as Windows service~~ — NSSM services installed, auto-start + failure recovery

---

## Blog Ideas

- [ ] "LLMs are border collies" - analogy for working with AI assistants (Slack #88-89)

---

## Version History

| Date | Change |
|------|--------|
| 01/31/2026 | Added new Slack items: index tables, watchlist tracking, coverage dashboard, data loader, PRICE partitioning, Boris coverage bug, Logo Writer project |
| 01/31/2026 | Completed PRICE optimization, stock split fix, Slack as Windows services. Added EODHD sources + news look-forward tasks |
| 01/25/2026 | Fixed dark mode code block highlight issue (#120), cleaned up all pending bugs |
| 01/21/2026 | Moved feature requests to ROADMAP.md (favicon, staging, Cloudflare IP, CI dashboard, Brinson) |
| 01/21/2026 | Synced with Slack inbox, reorganized by priority |
| 01/20/2026 | Pruned completed items and archived section to reduce context |
| 01/19/2026 | Cleaned up: Removed obsolete App Service quota check, marked favicon as done |
