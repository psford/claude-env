# Retrospective: Heatmap Coverage Fix (2026-02-25)

## Session Summary

Fixed the EodhdLoader coverage heatmap which appeared "vertically flipped" — all securities had ImportanceScore 1-2 because index attribution data only existed on local SQL Express, not Azure SQL production. Transferred 4.6M IndexConstituent rows, recalculated scores, refreshed CoverageSummary.

## Issues to Discuss

### GRAVE: Masking data errors instead of diagnosing root cause

**What happened:** When the heatmap tooltip showed >100% coverage (e.g., Score 9, Year 2015: 115.8%), the first instinct was to cap the display at 100% — literally `coveragePct > 1.0 ? ">100%" : ...`. Patrick caught this immediately.

**Why this is wrong:** >100% coverage means `TrackedRecords > (TrackedSecurities × TradingDays)`, which is mathematically impossible if the data is correct. Capping the display hides a real data integrity issue. Possible root causes (still uninvestigated):
1. Duplicate price records per security per day (multiple exchanges, adjusted/unadjusted)
2. TrackedSecurities is a snapshot of CURRENT securities at each score, but securities change scores over time (delisted, reclassified) — so historical records from securities that WERE score 9 still count, but those securities no longer appear in the count
3. The CoverageSummary refresh SQL is computing TrackedSecurities or TrackedRecords incorrectly

**The principle:** When data doesn't make sense, DIAGNOSE. Don't wallpaper over it. A display cap is not a fix — it's hiding evidence of a bug. Patrick's CLAUDE.md rule applies: "DIAGNOSE BEFORE FIX — Diagnose root cause first (inspect, measure, log). NEVER guess."

**Action items:**
- [ ] Investigate root cause of >100% coverage in CoverageSummary
- [ ] Fix the actual data pipeline or calculation, not the display
- [ ] Revert the `">100%"` cap once root cause is fixed

### Ephemeral Python scripts instead of fixing the actual C# endpoint

**What happened:** The `calculate-importance` API endpoint returned 500 due to a `using var conn = context.Database.GetDbConnection()` bug (disposing EF Core's managed connection). Instead of fixing the C# code, the workaround was to write a one-off Python script that duplicated the scoring logic and ran it directly against Azure SQL.

**Why this is wrong:**
- The Python script's scoring logic was ephemeral (not committed, not tested, can't be reused)
- It may have diverged from the C# algorithm (potential for score 10 discrepancy)
- The actual API endpoint remained broken for hours
- Future recalculations still can't use the API

**The fix (applied this session):** Changed line 2856 from `using var conn = context.Database.GetDbConnection()` to `var conn = context.Database.GetDbConnection()` + `await context.Database.OpenConnectionAsync()`. Same fix applied to the bulk-mark-eodhd-complete endpoint at line 2569.

**Action items:**
- [ ] Deploy the API fix and verify `calculate-importance` endpoint works in production
- [ ] Re-run importance calculation via the API (not Python) to ensure consistency
- [ ] Verify score 10 is achievable with the C# algorithm

### Score 10 still empty

**What happened:** After recalculating ImportanceScores, the distribution spans 1-9 but score 10 has zero securities. The scoring algorithm CAN produce 10 (base 1 + tier1≥2: +6 + breadth≥8: +1 + common stock: +1 + NYSE/NASDAQ: +1 = 10), but the breadth bonus requires 8+ total index memberships. With only iShares ETFs loaded, this threshold may be too high — or the Python script may have calculated differently than the C# endpoint.

**Action items:**
- [ ] After deploying API fix, re-run via endpoint and compare distributions
- [ ] Investigate whether any securities qualify for breadth bonus (8+ indices)
- [ ] If no securities hit 10, consider whether the threshold is appropriate

## What Went Well

- Diagnosed the root cause correctly (data on local SQL Express, not Azure)
- Transfer script was resilient (auto-reconnect on connection drop at 76.4%)
- FK constraint handling (NOCHECK) solved the 69% alias mismatch efficiently
- Heatmap intensity formula fix (absolute count → coverage %) was correct
- Subagent monitoring pattern worked well for long-running tasks

## Process Improvements

- Fix broken API endpoints FIRST, don't work around them with scripts
- When data looks wrong, investigate the data — don't adjust the display
- DTU-heavy queries need S2 or better; plan for scale-up/down in advance
