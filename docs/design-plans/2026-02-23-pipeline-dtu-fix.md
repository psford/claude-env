# Pipeline DTU Fix Design

## Summary

The stock price crawler pipeline suffers from DTU exhaustion on Azure SQL Basic (5 DTU) because two admin endpoints — the gap query and the refresh-summary — aggregate the full `data.Prices` table (43M+ rows). At 5 DTU, those full-table scans time out or starve other queries.

This design replaces both scans with reads against two new lightweight metadata tables kept up to date incrementally. Each time the crawler bulk-inserts a batch of prices, a small C# computation over the in-memory batch produces per-security deltas (count of new rows, min/max date, year breakdown). Those deltas are merged into `data.SecurityPriceCoverage` (one row per security, ~30K rows) and `data.SecurityPriceCoverageByYear` (one row per security per year, ~60K rows). The gap and refresh-summary endpoints then read from these small indexed tables instead of the 43M-row Prices table. Response shapes exposed to EodhdLoader are unchanged. A one-time backfill endpoint populates the new tables from existing Prices data to bootstrap the system.

## Definition of Done
1. A per-security metadata table tracks price coverage (count, first/last date), updated incrementally on every price load — eliminating the need to scan the 43M+ row Prices table for coverage stats.
2. The gap query becomes a batch queue builder: runs once at crawler startup to build a work queue, re-runs when the queue is nearly drained — not on every crawler request.
3. The refresh-summary (heatmap data) is rebuilt from the lightweight metadata table after crawl sessions, not from a full Prices table aggregation.
4. All of this works within the 5 DTU Azure SQL Basic budget without timeouts.

**Out of scope:** Changing the crawler's price-loading logic itself, UI changes to the heatmap/dashboard, importance scoring changes.

## Acceptance Criteria

### pipeline-dtu-fix.AC1: Per-security coverage metadata updated incrementally
- **pipeline-dtu-fix.AC1.1 Success:** After BulkInsertAsync inserts N new prices for a security, SecurityPriceCoverage.PriceCount increments by exactly N
- **pipeline-dtu-fix.AC1.2 Success:** After inserting prices with dates outside the existing range, FirstDate/LastDate widen to include the new dates
- **pipeline-dtu-fix.AC1.3 Success:** ExpectedCount reflects the business day count between FirstDate and LastDate per BusinessCalendar
- **pipeline-dtu-fix.AC1.4 Success:** Backfill endpoint populates coverage for all active securities, with PriceCount matching actual Prices row counts
- **pipeline-dtu-fix.AC1.5 Edge:** First-ever price insert for a security creates a new coverage row (MERGE INSERT path)
- **pipeline-dtu-fix.AC1.6 Edge:** Batch containing prices for multiple securities updates each security's coverage independently

### pipeline-dtu-fix.AC2: Gap query reads from coverage table
- **pipeline-dtu-fix.AC2.1 Success:** Gap endpoint returns securities where GapDays > 0 (have some prices but missing days)
- **pipeline-dtu-fix.AC2.2 Success:** Gap endpoint returns securities with no coverage row (zero prices loaded)
- **pipeline-dtu-fix.AC2.3 Success:** Gap endpoint excludes securities where GapDays = 0 (fully covered)
- **pipeline-dtu-fix.AC2.4 Success:** Response shape matches current format (SecurityAlias, TickerSymbol, ActualPriceCount, ExpectedPriceCount, MissingDays, etc.) for EodhdLoader compatibility
- **pipeline-dtu-fix.AC2.5 Failure:** Securities with IsEodhdComplete=1 or IsEodhdUnavailable=1 are excluded from gap results

### pipeline-dtu-fix.AC3: Refresh-summary aggregates from coverage metadata
- **pipeline-dtu-fix.AC3.1 Success:** Refresh-summary produces CoverageSummary rows with correct Year x ImportanceScore breakdown
- **pipeline-dtu-fix.AC3.2 Success:** TrackedRecords, UntrackedRecords, TrackedSecurities, UntrackedSecurities counts match what a full Prices scan would produce (verified during backfill)

### pipeline-dtu-fix.AC4: All operations within 5 DTU budget
- **pipeline-dtu-fix.AC4.1 Success:** Gap endpoint, refresh-summary, and incremental coverage updates each complete without timeout on Azure SQL Basic
- **pipeline-dtu-fix.AC4.2 Failure:** Concurrent gap query + coverage update does not cause DTU exhaustion or deadlock

## Glossary

- **DTU (Database Transaction Unit)**: Azure SQL's combined measure of CPU, memory, and I/O capacity. The Basic tier provides 5 DTU — a hard ceiling that causes query timeouts when exceeded.
- **EodhdLoader**: Companion WPF desktop app that calls the Stock Analyzer API gap endpoint to discover missing price data and fetches it from the EODHD data provider.
- **BulkInsertAsync**: The C# method in `SqlPriceRepository` that batches incoming price records into 1000-row chunks with per-batch deduplication. Coverage updates are added to this loop.
- **SecurityAlias**: Integer surrogate key identifying a security, corresponding to a row in `data.SecurityMaster`.
- **BusinessCalendar**: Pre-populated calendar table flagging each date as a business (trading) day or not. Used to compute expected price counts for a date range.
- **GapDays**: Computed persisted column on SecurityPriceCoverage — the difference between ExpectedCount and PriceCount. Positive value means missing price data.
- **CoverageSummary**: Existing pre-aggregation table storing Year x ImportanceScore breakdowns for the admin dashboard heatmap.
- **MERGE (SQL)**: SQL upsert statement — INSERT if row doesn't exist, UPDATE if it does — in a single atomic operation. Used to increment coverage counters.
- **Delta arithmetic**: Computing aggregate changes from the in-memory batch (count, min/max date) rather than re-querying the database.
- **Computed persisted column**: SQL Server column derived from an expression over other columns, calculated on each UPDATE and stored on disk for zero-cost reads.
- **Idempotent migration**: Migration safe to run multiple times without error, using `IF NOT EXISTS` guards around DDL.

## Architecture

Two new metadata tables — `data.SecurityPriceCoverage` (per-security totals) and `data.SecurityPriceCoverageByYear` (per-security-per-year counts) — replace all full Prices table scans. These tables are updated incrementally inside `BulkInsertAsync` after each batch of price insertions, using delta arithmetic from the in-memory insert batch rather than querying Prices.

The gap endpoint (`GET /api/admin/prices/gaps`) switches from a 4-CTE query scanning 43M+ Prices rows to a simple JOIN across SecurityMaster, SecurityPriceCoverage, and TrackedSecurities — all small indexed tables. The response shape stays the same for backward compatibility with EodhdLoader.

The refresh-summary endpoint (`POST /api/admin/dashboard/refresh-summary`) switches from aggregating the full Prices table to aggregating SecurityPriceCoverageByYear joined with SecurityMaster. The CoverageSummary output shape is unchanged.

### Data Flow

```
Price insertion (BulkInsertAsync)
  → Insert prices into data.Prices (existing)
  → MERGE delta into data.SecurityPriceCoverage (new)
  → MERGE delta into data.SecurityPriceCoverageByYear (new)
  → Compute ExpectedCount from BusinessCalendar (new)

Gap query (GET /api/admin/prices/gaps)
  → JOIN SecurityMaster + SecurityPriceCoverage + TrackedSecurities
  → Filter: IsTracked=1, GapDays > 0 OR no coverage row
  → Return same response shape as current

Refresh-summary (POST /api/admin/dashboard/refresh-summary)
  → Aggregate SecurityPriceCoverageByYear + SecurityMaster
  → DELETE + INSERT into CoverageSummary (same as current)
```

### Table Contracts

**data.SecurityPriceCoverage** — one row per security:

```sql
CREATE TABLE [data].[SecurityPriceCoverage] (
    SecurityAlias    int          NOT NULL PRIMARY KEY,
    PriceCount       int          NOT NULL DEFAULT 0,
    FirstDate        date         NULL,
    LastDate         date         NULL,
    ExpectedCount    int          NULL,
    GapDays          AS (ISNULL(ExpectedCount, 0) - PriceCount) PERSISTED,
    LastUpdatedAt    datetime2    NOT NULL DEFAULT GETUTCDATE(),
    CONSTRAINT FK_SecurityPriceCoverage_SecurityMaster
        FOREIGN KEY (SecurityAlias) REFERENCES data.SecurityMaster(SecurityAlias)
);
```

- `GapDays` is a computed persisted column — zero read cost, auto-maintained on UPDATE.
- `ExpectedCount` is the number of business days between FirstDate and LastDate, computed from `data.BusinessCalendar` during the MERGE via correlated subquery.
- Securities with no prices have no row (handled by LEFT JOIN + IS NULL in gap query).

**data.SecurityPriceCoverageByYear** — one row per security per year:

```sql
CREATE TABLE [data].[SecurityPriceCoverageByYear] (
    SecurityAlias    int          NOT NULL,
    [Year]           int          NOT NULL,
    PriceCount       int          NOT NULL DEFAULT 0,
    LastUpdatedAt    datetime2    NOT NULL DEFAULT GETUTCDATE(),
    CONSTRAINT PK_SecurityPriceCoverageByYear
        PRIMARY KEY (SecurityAlias, [Year]),
    CONSTRAINT FK_SecurityPriceCoverageByYear_SecurityMaster
        FOREIGN KEY (SecurityAlias) REFERENCES data.SecurityMaster(SecurityAlias)
);
```

- Estimated size: ~60K rows (30K securities x 2 years average).
- Supports the Year dimension needed by CoverageSummary aggregation.

### Incremental Update Contract

After each batch in `BulkInsertAsync`, for each distinct SecurityAlias in the inserted prices:

```csharp
// Delta computed in C# from the newPrices list — no Prices table scan
var deltas = newPrices
    .GroupBy(p => p.SecurityAlias)
    .Select(g => new {
        SecurityAlias = g.Key,
        InsertedCount = g.Count(),
        MinDate = g.Min(p => p.EffectiveDate),
        MaxDate = g.Max(p => p.EffectiveDate),
        YearCounts = g.GroupBy(p => p.EffectiveDate.Year)
                      .ToDictionary(y => y.Key, y => y.Count())
    });
```

Each delta triggers:
1. MERGE into SecurityPriceCoverage: increment PriceCount, widen FirstDate/LastDate, recompute ExpectedCount from BusinessCalendar.
2. MERGE into SecurityPriceCoverageByYear: increment PriceCount for each (SecurityAlias, Year) pair.

### Gap Endpoint Query (replacement)

```sql
SELECT
    sm.SecurityAlias, sm.TickerSymbol, sm.IsTracked,
    pc.FirstDate, pc.LastDate,
    ISNULL(pc.PriceCount, 0) AS ActualPriceCount,
    ISNULL(pc.ExpectedCount, (SELECT COUNT(*) FROM data.BusinessCalendar bc
        WHERE bc.IsBusinessDay = 1
        AND bc.EffectiveDate >= DATEADD(YEAR, -2, GETDATE())
        AND bc.EffectiveDate <= GETDATE())) AS ExpectedPriceCount,
    CASE WHEN pc.SecurityAlias IS NULL
         THEN (SELECT COUNT(*) FROM data.BusinessCalendar bc
               WHERE bc.IsBusinessDay = 1
               AND bc.EffectiveDate >= DATEADD(YEAR, -2, GETDATE())
               AND bc.EffectiveDate <= GETDATE())
         ELSE pc.GapDays END AS MissingDays,
    sm.ImportanceScore,
    COALESCE(ts.Priority, 999) AS Priority
FROM data.SecurityMaster sm WITH (NOLOCK)
LEFT JOIN data.SecurityPriceCoverage pc WITH (NOLOCK)
    ON pc.SecurityAlias = sm.SecurityAlias
LEFT JOIN data.TrackedSecurities ts WITH (NOLOCK)
    ON ts.SecurityAlias = sm.SecurityAlias
WHERE sm.IsActive = 1
    AND sm.IsEodhdUnavailable = 0
    AND sm.IsEodhdComplete = 0
    AND sm.IsTracked = 1
    AND (pc.SecurityAlias IS NULL OR pc.GapDays > 0)
ORDER BY Priority, MissingDays DESC, sm.TickerSymbol
```

Joins three small tables (~30K rows each). Sub-second on 5 DTU.

### Refresh-Summary Query (replacement)

```sql
SELECT
    cy.[Year],
    sm.ImportanceScore AS Score,
    SUM(CASE WHEN sm.IsTracked = 1 THEN cy.PriceCount ELSE 0 END) AS TrackedRecords,
    SUM(CASE WHEN sm.IsTracked = 0 THEN cy.PriceCount ELSE 0 END) AS UntrackedRecords,
    SUM(CASE WHEN sm.IsTracked = 1 THEN 1 ELSE 0 END) AS TrackedSecurities,
    SUM(CASE WHEN sm.IsTracked = 0 THEN 1 ELSE 0 END) AS UntrackedSecurities,
    (SELECT COUNT(DISTINCT bc.EffectiveDate)
     FROM data.BusinessCalendar bc WITH (NOLOCK)
     WHERE bc.IsBusinessDay = 1 AND YEAR(bc.EffectiveDate) = cy.[Year]) AS TradingDays
FROM data.SecurityPriceCoverageByYear cy WITH (NOLOCK)
INNER JOIN data.SecurityMaster sm WITH (NOLOCK) ON sm.SecurityAlias = cy.SecurityAlias
WHERE sm.IsActive = 1
GROUP BY cy.[Year], sm.ImportanceScore
ORDER BY cy.[Year], Score
```

Aggregates ~60K rows instead of 43M+. Remainder of the endpoint (DELETE + INSERT into CoverageSummary, cache invalidation) stays the same.

## Existing Patterns

**Pre-aggregation tables.** The existing `data.CoverageSummary` table ([CoverageSummaryEntity.cs](projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/CoverageSummaryEntity.cs)) is already a pre-aggregation of Prices data for the heatmap. This design extends the same pattern: pre-aggregate coverage stats into lightweight tables, query those instead of Prices.

**EF Core migrations with idempotent raw SQL.** The recent `CreateIndexTablesIfNotExist` migration ([20260223232008](projects/stock-analyzer/src/StockAnalyzer.Core/Data/Migrations/20260223232008_CreateIndexTablesIfNotExist.cs)) established a pattern of `IF NOT EXISTS` guards for tables that may already exist locally. The new migration follows this pattern.

**Entity classes in `StockAnalyzer.Core/Data/Entities/`.** All domain entities live here with XML doc comments. New coverage entities follow the same convention.

**Batch processing with dedup.** `BulkInsertAsync` in [SqlPriceRepository.cs:110](projects/stock-analyzer/src/StockAnalyzer.Core/Data/SqlPriceRepository.cs#L110) processes in 1000-row batches with per-batch deduplication. Coverage updates are added to the same batch loop, maintaining the existing flow.

**NOLOCK for read-only analytics.** All read-only admin queries use `WITH (NOLOCK)` hints. Coverage table reads follow this pattern.

**Concurrency guard on refresh-summary.** The existing semaphore pattern on refresh-summary ([Program.cs:3255](projects/stock-analyzer/src/StockAnalyzer.Api/Program.cs#L3255)) stays in place.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Database Schema & EF Core Mapping
**Goal:** Create the two coverage tables and their EF Core entity/configuration mappings.

**Components:**
- EF Core migration in `StockAnalyzer.Core/Data/Migrations/` — creates `data.SecurityPriceCoverage` and `data.SecurityPriceCoverageByYear` with idempotent `IF NOT EXISTS` guards
- `SecurityPriceCoverageEntity` in `StockAnalyzer.Core/Data/Entities/`
- `SecurityPriceCoverageByYearEntity` in `StockAnalyzer.Core/Data/Entities/`
- DbContext registration in `StockAnalyzer.Core/Data/StockAnalyzerDbContext.cs` — DbSet properties and Fluent API configuration (schema, keys, computed column, FK)

**Dependencies:** None (first phase)

**Done when:** Migration applies cleanly on local SQL Express, tables exist in `data` schema, `dotnet build` succeeds
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Incremental Coverage Updates
**Goal:** After each price batch insertion, update both coverage tables using in-memory delta arithmetic (no Prices table scan).

**Components:**
- Coverage update logic in `SqlPriceRepository.cs` — added after each batch's `SaveChangesAsync()` in `BulkInsertAsync`
- MERGE statements for SecurityPriceCoverage (increment PriceCount, widen date range, recompute ExpectedCount from BusinessCalendar)
- MERGE statements for SecurityPriceCoverageByYear (increment PriceCount per year)

**Dependencies:** Phase 1 (tables must exist)

**Covers:** `pipeline-dtu-fix.AC1.1`, `pipeline-dtu-fix.AC1.2`, `pipeline-dtu-fix.AC1.3`, `pipeline-dtu-fix.AC4.1`

**Done when:** Inserting prices via BulkInsertAsync correctly updates both coverage tables; PriceCount increments match inserted row counts; FirstDate/LastDate reflect actual date range; ExpectedCount computed from BusinessCalendar
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Gap Endpoint Replacement
**Goal:** Replace the expensive 4-CTE gap query with a lightweight join against SecurityPriceCoverage.

**Components:**
- Replacement SQL in `Program.cs` gap endpoint (`GET /api/admin/prices/gaps`) — same response shape, reads from coverage table
- Handle securities with no coverage row (no prices at all) via LEFT JOIN + IS NULL
- Preserve ordering by Priority, MissingDays DESC, TickerSymbol

**Dependencies:** Phase 1 (tables), Phase 2 (data populated by inserts)

**Covers:** `pipeline-dtu-fix.AC2.1`, `pipeline-dtu-fix.AC2.2`, `pipeline-dtu-fix.AC2.3`, `pipeline-dtu-fix.AC4.1`

**Done when:** Gap endpoint returns correct results from coverage table; securities with gaps appear; securities with no prices appear; complete securities excluded; response matches EodhdLoader's expected shape; timeout reduced from 300s to 30s or less
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Refresh-Summary Replacement
**Goal:** Replace the full Prices table scan in refresh-summary with a CoverageByYear aggregation.

**Components:**
- Replacement SQL in `Program.cs` refresh-summary endpoint (`POST /api/admin/dashboard/refresh-summary`)
- Aggregates from SecurityPriceCoverageByYear joined with SecurityMaster
- TradingDays computed from BusinessCalendar per-year (small table)
- Existing DELETE + INSERT into CoverageSummary and cache invalidation unchanged

**Dependencies:** Phase 1 (tables), Phase 2 (data populated by inserts)

**Covers:** `pipeline-dtu-fix.AC3.1`, `pipeline-dtu-fix.AC3.2`, `pipeline-dtu-fix.AC4.1`

**Done when:** Refresh-summary produces identical CoverageSummary rows as the current Prices-based query; executes in seconds, not minutes; timeout reduced from 300s to 30s or less
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Coverage Backfill
**Goal:** Provide a mechanism to populate coverage tables from existing Prices data (one-time bootstrap).

**Components:**
- Admin endpoint in `Program.cs` (`POST /api/admin/prices/backfill-coverage`) — scans Prices once to seed both coverage tables
- Concurrency guard (semaphore) to prevent concurrent execution
- Progress logging during the scan
- Idempotent: safe to re-run (MERGE, not INSERT)

**Dependencies:** Phase 1 (tables must exist)

**Covers:** `pipeline-dtu-fix.AC1.4`, `pipeline-dtu-fix.AC4.1`

**Done when:** Backfill endpoint populates both coverage tables from existing Prices data; coverage row counts match SecurityMaster active securities; PriceCount per security matches actual Prices row count
<!-- END_PHASE_5 -->

## Additional Considerations

**Backfill on production.** The backfill scans 43M+ Prices rows — this is the one allowed "expensive" operation. On Azure SQL Basic (5 DTU), it will take several minutes. Run during off-hours via the admin endpoint. After this one-time scan, no endpoint ever touches the full Prices table for coverage stats again.

**Data consistency.** Coverage tables are eventually consistent. If the API process crashes between inserting prices and updating coverage, coverage will be stale until the next backfill or manual correction. This is acceptable for a prototype — the crawler will simply re-fetch prices that appear as gaps, and dedup will skip them.

**Future: price deletion.** No price deletion endpoints exist today. If one is added, it must decrement coverage tables. This is a future concern, not current scope.
