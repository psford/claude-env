# While You Were Away

Scratchpad for quick notes and pending tasks.

**For feature requests:** Add to [ROADMAP.md](projects/stock-analyzer/ROADMAP.md) instead.

---

## Pending Tasks

### Bugs / Immediate Fixes
- [ ] Privacy page is busted (Slack #153)

### High Priority
- [ ] **Stage environment in Azure** — same DBs/endpoints, NOT psfordtaurus.com, ability to test then rotate to prod near-instantly (Slack #155)
- [ ] **Rebuild news sentiment analyzer** — MSFT moved 6% in a day and analyzer couldn't figure out why (Slack #156)
- [ ] **PRICE table optimization plan** — 7M+ rows on Azure SQL Basic (5 DTU), needs partitioning/archiving strategy

### Research
- [ ] Compile Slack listener as standalone Windows service that runs regardless of app/Claude status (Slack #154)
- [ ] Review ed3d-plugins: https://github.com/ed3dai/ed3d-plugins — evaluate methodology, dependencies, comparison to current approach (Slack #152)

---

## Blog Ideas

- [ ] "LLMs are border collies" - analogy for working with AI assistants (Slack #88-89)

---

## Version History

| Date | Change |
|------|--------|
| 01/25/2026 | Fixed dark mode code block highlight issue (#120), cleaned up all pending bugs |
| 01/21/2026 | Moved feature requests to ROADMAP.md (favicon, staging, Cloudflare IP, CI dashboard, Brinson) |
| 01/21/2026 | Synced with Slack inbox, reorganized by priority |
| 01/20/2026 | Pruned completed items and archived section to reduce context |
| 01/19/2026 | Cleaned up: Removed obsolete App Service quota check, marked favicon as done |
