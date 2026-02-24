# Pipeline DTU Fix - Human Test Plan

**Implementation Plan:** `docs/implementation-plans/2026-02-23-pipeline-dtu-fix/`
**Branch:** `feature/pipeline-dtu-fix`
**Date:** 2026-02-24

---

## Automated Test Summary

| Test File | Type | AC Coverage | Status |
|---|---|---|---|
| `SqlPriceRepositoryCoverageTests.cs` (10 tests) | Unit | AC1.1, AC1.6 | PASS |
| `CoverageIntegrationTests.cs` (6 tests) | Integration (SQL Express) | AC1.2, AC1.3, AC1.5 | PASS |

**Run command:** `dotnet test projects/stock-analyzer/StockAnalyzer.sln`

---

## Human Verification Steps

### Pre-Requisites

1. Deploy the `feature/pipeline-dtu-fix` branch to a test environment (or run locally)
2. Ensure SQL Express is running locally (`net start MSSQL$SQLEXPRESS`)
3. Ensure the API is running on localhost:5000
4. Coverage tables should be empty before starting (fresh state)

---

### HT-1: Gap Endpoint — Empty Coverage Tables (AC2.2)

**Goal:** Verify that securities with no coverage row appear in gap results with `actualDays = 0`.

**Steps:**
1. Confirm coverage tables are empty: `SELECT COUNT(*) FROM data.SecurityPriceCoverage` should return 0
2. Call `GET http://localhost:5000/api/admin/prices/gaps`
3. Verify HTTP 200 response within 30 seconds

**Expected Results:**
- All tracked securities appear in the `gaps` array
- Every gap entry has `actualDays = 0`
- Every gap entry has `missingDays > 0` (equal to `expectedDays`)
- `firstDate` and `lastDate` are non-null, formatted as `yyyy-MM-dd`
- `summary.securitiesWithData` = 0

---

### HT-2: Backfill Endpoint (AC1.4)

**Goal:** Verify backfill populates coverage tables with correct counts matching Prices table.

**Steps:**
1. Call `POST http://localhost:5000/api/admin/prices/backfill-coverage`
2. Wait for completion (may take several minutes on large datasets)
3. Verify HTTP 200 with `success: true`

**Expected Results:**
- `SecurityPriceCoverage` row count matches distinct SecurityAlias count in Prices table:
  ```sql
  SELECT COUNT(*) FROM data.SecurityPriceCoverage
  -- should equal:
  SELECT COUNT(DISTINCT SecurityAlias) FROM data.Prices
  ```
- Spot-check 5 securities — PriceCount matches actual Prices rows:
  ```sql
  SELECT pc.SecurityAlias, pc.PriceCount, COUNT(p.SecurityAlias) AS ActualCount
  FROM data.SecurityPriceCoverage pc
  JOIN data.Prices p ON p.SecurityAlias = pc.SecurityAlias
  WHERE pc.SecurityAlias IN (SELECT TOP 5 SecurityAlias FROM data.SecurityPriceCoverage ORDER BY NEWID())
  GROUP BY pc.SecurityAlias, pc.PriceCount
  HAVING pc.PriceCount <> COUNT(p.SecurityAlias)
  ```
  Expected: zero rows returned (all match)

---

### HT-3: Gap Endpoint — After Backfill (AC2.1, AC2.3, AC2.5)

**Goal:** Verify gap endpoint correctly filters after coverage tables are populated.

**Steps:**
1. Call `GET http://localhost:5000/api/admin/prices/gaps`
2. Verify HTTP 200 within 30 seconds

**Expected Results:**
- **AC2.1:** All gap entries have `missingDays > 0` (partial coverage)
- **AC2.3:** No gap entry has `missingDays = 0` (fully covered excluded)
- **AC2.3:** `summary.securitiesComplete > 0` (some securities are fully covered)
- **AC2.5:** No securities with `IsEodhdComplete=1` or `IsEodhdUnavailable=1` in results:
  ```sql
  -- Get all SecurityAlias values from the gaps response, then:
  SELECT SecurityAlias FROM data.SecurityMaster
  WHERE SecurityAlias IN (<gap_aliases>)
    AND (IsEodhdComplete = 1 OR IsEodhdUnavailable = 1)
  ```
  Expected: zero rows

---

### HT-4: Response Shape — EodhdLoader Compatibility (AC2.4)

**Goal:** Verify JSON response structure matches EodhdLoader DTO contract exactly.

**Steps:**
1. Call `GET http://localhost:5000/api/admin/prices/gaps`
2. Inspect the JSON response structure

**Expected Results:**
- Root keys present: `success`, `market`, `includeUntracked`, `summary`, `completionPercent`, `gaps`
- Summary keys present: `totalSecurities`, `totalTrackedSecurities`, `totalUntrackedSecurities`, `securitiesWithData`, `securitiesWithGaps`, `trackedWithGaps`, `untrackedWithGaps`, `securitiesComplete`, `totalPriceRecords`, `totalMissingDays`
- Each gap item has keys: `securityAlias`, `ticker`, `isTracked`, `firstDate`, `lastDate`, `actualDays`, `expectedDays`, `missingDays`, `importanceScore`
- `firstDate` and `lastDate` formatted as `yyyy-MM-dd` (e.g., `"2024-01-15"`)
- `totalPriceRecords > 0` (re-enabled from coverage table SUM, was previously hardcoded to 0)

---

### HT-5: Refresh Summary — CoverageByYear Aggregation (AC3.1, AC3.2)

**Goal:** Verify refresh-summary produces correct Year x ImportanceScore breakdown from CoverageByYear.

**Steps:**
1. Call `POST http://localhost:5000/api/admin/dashboard/refresh-summary`
2. Verify HTTP 200 with `success: true` and `cellCount > 0`

**Expected Results:**
- **AC3.1:** CoverageSummary table has rows with Year x ImportanceScore groupings:
  ```sql
  SELECT Year, ImportanceScore, TrackedRecords, TrackedSecurities
  FROM data.CoverageSummary
  WHERE TrackedRecords > 0
  ORDER BY Year, ImportanceScore
  ```
  Should show meaningful data for years with known price history
- **AC3.2:** Spot-check one Year x ImportanceScore cell against Prices:
  ```sql
  -- Pick a specific Year/ImportanceScore from CoverageSummary, then verify:
  SELECT COUNT(*) AS ActualCount
  FROM data.Prices p
  JOIN data.SecurityMaster sm ON sm.SecurityAlias = p.SecurityAlias
  WHERE YEAR(p.EffectiveDate) = <Year>
    AND sm.ImportanceScore = <Score>
    AND sm.IsTracked = 1
  ```
  TrackedRecords in CoverageSummary should match ActualCount

---

### HT-6: DTU Budget — Timing Verification (AC4.1)

**Goal:** Verify all operations complete within timeout on 5 DTU budget.

**Steps:**
1. Time each endpoint call:
   - `GET /api/admin/prices/gaps` — should complete in < 30 seconds
   - `POST /api/admin/dashboard/refresh-summary` — should complete in < 30 seconds
   - `POST /api/admin/prices/backfill-coverage` — should complete (600s timeout, expected < 5 min)
2. Optionally run: `python helpers/test_dtu_endpoints.py`

**Expected Results:**
- All endpoints return HTTP 200 without timeout
- No SQL timeout exceptions in application logs
- On Azure: DTU monitor shows no sustained spikes above 80%

---

### HT-7: Concurrent Safety — Design Verification (AC4.2)

**Goal:** Verify no deadlock between gap query reads and coverage update writes.

**Code Review Checklist:**
- [ ] Gap endpoint SQL: every table reference has `WITH (NOLOCK)` — SecurityMaster, SecurityPriceCoverage, TrackedSecurities, BusinessCalendar
- [ ] `UpdateCoverageAsync` MERGE: `WITH (HOLDLOCK)` is only on MERGE targets (coverage tables)
- [ ] Backfill endpoint MERGE: `WITH (HOLDLOCK)` is only on MERGE targets
- [ ] No UPDLOCK, XLOCK, or other escalating lock hints on shared tables
- [ ] Refresh-summary: `WITH (NOLOCK)` on all read tables + semaphore guard prevents concurrent runs

**Observational Verification (post-deployment):**
1. During a live EODHD crawler run (which triggers incremental coverage updates), call the gap endpoint 3-5 times
2. All calls should return HTTP 200 without delay
3. Check application logs for SQL error 1205 (deadlock) — should be zero
4. Check Azure DTU monitor — no spike during concurrent operations

---

### HT-8: Incremental Coverage Update After Live Price Insert (AC1.1, AC1.2, AC1.6)

**Goal:** Verify that loading new prices via the normal pipeline updates coverage incrementally.

**Steps:**
1. Note current coverage state for a specific security:
   ```sql
   SELECT * FROM data.SecurityPriceCoverage WHERE SecurityAlias = <known_alias>
   ```
2. Trigger a price load for that security (via EODHD loader or test insert)
3. Check coverage again after load completes

**Expected Results:**
- **AC1.1:** PriceCount incremented by exactly the number of new prices inserted
- **AC1.2:** If new prices extend the date range, FirstDate/LastDate widened accordingly
- **AC1.6:** Other securities' coverage rows remain unchanged (independent updates)
- LastUpdatedAt is recent (within seconds of the insert)
- CoverageByYear rows updated for affected years only

---

## Sign-Off

| Verification | Tester | Date | Pass/Fail | Notes |
|---|---|---|---|---|
| HT-1: Empty coverage gaps | | | | |
| HT-2: Backfill endpoint | | | | |
| HT-3: Post-backfill gaps | | | | |
| HT-4: Response shape | | | | |
| HT-5: Refresh summary | | | | |
| HT-6: DTU timing | | | | |
| HT-7: Concurrent safety | | | | |
| HT-8: Incremental update | | | | |
