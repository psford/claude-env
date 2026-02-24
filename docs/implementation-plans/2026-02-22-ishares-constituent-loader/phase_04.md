# iShares Constituent Loader — Phase 4: Polish and Verification

**Goal:** End-to-end verification of rate limiting enforcement, pipeline output parity with Python, codebase cleanup of all Wikipedia scraper references, and final build validation.

**Architecture:** Verification-focused phase with unit tests for rate limiting behavior, integration test fixtures for comparing C# parser output against known-good Python output, automated codebase scanning for stale references, and build/run validation. All tests use xUnit + Moq, consistent with the test project created in Phase 1.

**Tech Stack:** C# / xUnit / Moq, Python (helpers/ishares_ingest.py for reference output generation), grep/search for cleanup verification

**Scope:** 4 phases from original design (this is phase 4 of 4)

**Codebase verified:** 2026-02-22

---

## Acceptance Criteria Coverage

This phase implements and tests:

### ishares-constituent-loader.AC6: Cross-Cutting
- **ishares-constituent-loader.AC6.1 Success:** Rate limiting enforces minimum 2s between iShares HTTP requests
- **ishares-constituent-loader.AC6.2 Success:** C# output matches Python pipeline output for IVV and IJK (row counts, weight values within rounding tolerance)
- **ishares-constituent-loader.AC6.3 Success:** No references to Wikipedia scraper remain in codebase after refactor
- **ishares-constituent-loader.AC6.4 Success:** App builds and runs with new service registered in DI

---

## Reference Files

The executor should read these files for context:

- **IISharesConstituentService (Phase 1):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/Services/IISharesConstituentService.cs`
  - Interface definition: `IngestEtfAsync`, `IngestAllEtfsAsync`, `EtfConfigs`, events
  - Rate limiting constant: `RequestDelayMs = 2000` in service implementation
- **ISharesConstituentService (Phase 1):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/Services/ISharesConstituentService.cs`
  - `IngestAllEtfsAsync` implementation — contains the rate-limiting `Task.Delay` loop
- **IndexManagerViewModel (Phase 2):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/ViewModels/IndexManagerViewModel.cs`
  - `LoadAllAsync` — calls `IngestAllEtfsAsync` or `IngestEtfAsync` based on selection
- **CrawlerViewModel (Phase 3):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/ViewModels/CrawlerViewModel.cs`
  - `CheckAndLoadConstituentsAsync` — calls `IngestEtfAsync` in loop with 2s delay
- **Python pipeline:** `c:/Users/patri/Documents/claudeProjects/helpers/ishares_ingest.py`
  - Rate limit constant: line 67 (`REQUEST_DELAY_SECONDS = 2.0`)
  - Stats structure: lines 428-436 (parsed, matched, created, inserted, skipped_existing, failed)
  - IVV ingest output format: lines 510-515
- **Format A sample (Phase 1):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/tests/EodhdLoader.Tests/TestData/format_a_sample.json`
- **Format B sample (Phase 1):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/tests/EodhdLoader.Tests/TestData/format_b_sample.json`
- **App.xaml.cs:** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/App.xaml.cs`
- **EodhdLoader.csproj:** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->
## Subcomponent A: Rate Limiting Verification

<!-- START_TASK_1 -->
### Task 1: Rate Limiting Tests

**Verifies:** ishares-constituent-loader.AC6.1

**Files:**
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/Integration/RateLimitingTests.cs`

**Implementation:**

Rate limiting is enforced in two places:
1. **`ISharesConstituentService.IngestAllEtfsAsync`** — iterates all configured ETFs with `Task.Delay(RequestDelayMs)` between each `IngestEtfAsync` call
2. **`CrawlerViewModel.CheckAndLoadConstituentsAsync`** — iterates stale ETFs with `Task.Delay(2000)` between each call

Both paths must enforce a minimum 2-second gap between consecutive iShares HTTP requests.

**Testing approach:** Mock `IISharesConstituentService` and record timestamps of each `IngestEtfAsync` invocation. Assert consecutive calls are spaced >= 1.9 seconds apart (0.1s tolerance for timer jitter).

**Test 1: `IngestAllEtfsAsync_EnforcesMinimum2sDelayBetweenRequests`**

This tests the service's own loop. Since `IngestAllEtfsAsync` is on the service implementation (not the interface mock), this test needs the real service with a mocked `HttpMessageHandler` that returns instantly. The test:
1. Create a real `ISharesConstituentService` with mock HTTP handler that returns valid but empty JSON (`{"aaData": []}`) for any request
2. Use EF Core InMemory provider for `StockAnalyzerDbContext`
3. Configure `EtfConfigs` to contain only 3 ETFs (to keep test runtime under 10s)
4. Call `IngestAllEtfsAsync()`
5. Record HTTP request timestamps from the mock handler
6. Assert each consecutive pair has >= 1.9s gap

**Test 2: `CrawlerConstituentPreStep_EnforcesMinimum2sDelayBetweenRequests`**

This tests the Crawler's loop. Uses `Mock<IISharesConstituentService>`:
1. Mock `GetStaleEtfsAsync` to return 3 stale ETFs
2. Mock `IngestEtfAsync` to record `DateTime.UtcNow` on each invocation and return successful `IngestStats`
3. Instantiate `CrawlerViewModel` with mocked dependencies
4. Call `CheckAndLoadConstituentsAsync` (may need to be made `internal` with `InternalsVisibleTo`, or test via `StartCrawlAsync` with the rest of the flow mocked out)
5. Assert 3 calls to `IngestEtfAsync` occurred
6. Assert consecutive call timestamps have >= 1.9s gap

Note: These tests are intentionally slow (~6s each) because they verify real timing behavior. Mark with `[Trait("Category", "Slow")]` so they can be excluded from fast CI runs.

**Verification:**
Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/ --filter "FullyQualifiedName~RateLimitingTests"`
Expected: All tests pass (runtime ~12-15s total)

**Commit:** `test(eodhd-loader): add rate limiting verification tests for AC6.1`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Pipeline Parity Tests

**Verifies:** ishares-constituent-loader.AC6.2

**Files:**
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/Integration/PipelineParityTests.cs`

**Implementation:**

Verify that the C# parser produces identical output to the Python pipeline for the same input data. This reuses the same test fixture JSON files created in Phase 1 Task 9 (`format_a_sample.json` for IVV Format A, `format_b_sample.json` for IJK Format B). The expected values are derived directly from the fixture data and the Python parsing logic — no separate reference files or manual Python runs needed.

**How to derive expected values:** The test fixtures created in Phase 1 Task 9 contain a known set of rows (2-3 equity holdings, 1 Cash/Futures row, 1 holding with missing weight). The executor knows exactly what the fixture contains because they wrote it. The parity tests assert that C# produces the same parsed output as you'd get from the Python `parse_holdings()` function on the same data.

**Test 1: `FormatA_ParseOutput_MatchesPythonPipeline`**
1. Load `format_a_sample.json` test fixture (created in Phase 1 Task 9)
2. Parse with C# `ParseHoldings` method
3. Assert equity count equals the number of equity rows in the fixture (excluding Cash/Futures rows)
4. Assert the first holding's ticker, name, sector match the fixture's first equity row
5. Assert weight was divided by 100 (source percentage → decimal): e.g., if fixture has weight `6.54`, parsed weight should be `0.0654m`
6. Assert market value extracted from `{display, raw}` JSON object structure (Format A style)

**Test 2: `FormatB_ParseOutput_MatchesPythonPipeline`**
1. Load `format_b_sample.json` test fixture
2. Parse with C# `ParseHoldings` method
3. Assert equity count matches expected (excluding non-equity)
4. Assert weight comes from column index 17 (Format B) not column index 5 (Format A)
5. Assert sector comes from column index 3 (Format B) not column index 2 (Format A)

**Test 3: `WeightConversion_PercentageToDecimal_ConsistentWithPython`**
1. Parse a fixture containing a holding with known weight (e.g., `6.5432` as percentage)
2. Assert C# produces `0.065432m` (divided by 100)
3. Parse a fixture with weight as `"-"` → assert `null`
4. Parse a fixture with weight as `0.0` → assert `0m`
5. This catches the common bug of forgetting to divide by 100 or mishandling sentinel values

**Test 4: `NonEquityFiltering_ExcludesSameRowsAsPython`**
1. Parse a fixture containing rows for: Equity, Cash, Futures, Money Market, Cash Collateral and Margins
2. Assert only Equity rows remain in parsed output
3. Assert the count equals total rows minus non-equity rows
4. Python's filter set (ishares_ingest.py:191-194): `{"Cash", "Cash Collateral and Margins", "Cash and/or Derivatives", "Futures", "Money Market"}`

**Verification:**
Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/ --filter "FullyQualifiedName~PipelineParityTests"`
Expected: All tests pass

**Commit:** `test(eodhd-loader): add pipeline parity tests for AC6.2 (C# matches Python output)`
<!-- END_TASK_2 -->
<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 3-4) -->
## Subcomponent B: Cleanup and Build Verification

<!-- START_TASK_3 -->
### Task 3: Wikipedia Scraper Cleanup Verification

**Verifies:** ishares-constituent-loader.AC6.3

**Files:**
- No new files — verification only

**Implementation:**

Phase 2 (Task 6) deletes `IndexService.cs` and Phase 2 (Task 5) removes its DI registration. This task verifies nothing was missed.

**Step 1: Automated scan**

Run these searches across the entire eodhd-loader project directory to confirm zero references remain:

```bash
# Search for Wikipedia references
grep -ri "wikipedia" projects/eodhd-loader/src/ --include="*.cs" --include="*.xaml"

# Search for old IndexService class references
grep -ri "IndexService" projects/eodhd-loader/src/ --include="*.cs" --include="*.xaml"

# Search for old DTO names that lived inside IndexService.cs
grep -ri "IndexConstituentsResponse" projects/eodhd-loader/src/ --include="*.cs"

# Search for Wikipedia URLs
grep -ri "en.wikipedia.org" projects/eodhd-loader/src/ --include="*.cs"
```

**Expected results:** All four searches return zero matches.

**Step 2: If any matches found**

Fix them:
- Remove stale `using` statements referencing `IndexService`
- Remove any commented-out Wikipedia code
- Remove any stale XML doc comments mentioning Wikipedia
- Rebuild to verify nothing breaks

**Verification:**
Run: All four grep commands above return zero matches
Run: `dotnet build projects/eodhd-loader/EodhdLoader.sln`
Expected: Build succeeds, no references to Wikipedia or IndexService remain

**Commit:** `refactor(eodhd-loader): remove any remaining Wikipedia scraper references` (only if changes were needed; skip commit if scan was clean)
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Full Build and Smoke Test

**Verifies:** ishares-constituent-loader.AC6.4

**Files:**
- No new files — verification only

**Implementation:**

Final end-to-end verification that the complete solution builds and passes all tests.

**Step 1: Clean build**

```bash
dotnet build projects/eodhd-loader/EodhdLoader.sln -c Release --no-incremental
```

Expected: Build succeeds with zero errors and zero warnings related to missing types or unresolved references.

**Step 2: Run full test suite**

```bash
dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/ --verbosity normal
```

Expected: All tests pass (Phase 1 download/parsing/persistence tests + Phase 2 ViewModel tests + Phase 3 staleness/crawler tests + Phase 4 rate limiting/parity tests).

**Step 3: DI validation**

Verify the DI container can resolve all services without errors by checking App.xaml.cs registrations:
- `IISharesConstituentService` is registered via `AddHttpClient<IISharesConstituentService, ISharesConstituentService>()`
- `IndexManagerViewModel` constructor takes `IISharesConstituentService` (resolved by DI)
- `CrawlerViewModel` constructor takes `IISharesConstituentService` (resolved by DI)
- No remaining references to `IndexService` in the DI container
- `StockAnalyzerDbContext` is registered (required by `ISharesConstituentService`)

This is verified by the build itself (DI constructor parameters must match registered types) and by launching the app:

```bash
# Build and attempt launch (will fail if DI is misconfigured)
dotnet run --project projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj -c Release
```

Expected: App window appears without DI-related exceptions in output. Close the app after verifying it launches.

**Step 4: Document completion**

Log a summary of all phases completed:
- Phase 1: Core service (12 tasks) — download, parse, persist
- Phase 2: UI refactor (6 tasks) — ViewModel, XAML, cleanup
- Phase 3: Crawler integration (4 tasks) — staleness detection, pre-step
- Phase 4: Verification (4 tasks) — rate limiting, parity, cleanup, build

**Verification:**
Run: `dotnet build projects/eodhd-loader/EodhdLoader.sln -c Release --no-incremental`
Expected: Build succeeds

Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/`
Expected: All tests pass

**Commit:** `chore(eodhd-loader): verify full build and test suite for iShares constituent loader`
<!-- END_TASK_4 -->
<!-- END_SUBCOMPONENT_B -->
