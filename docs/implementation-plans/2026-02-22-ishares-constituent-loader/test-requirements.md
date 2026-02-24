# iShares Constituent Loader — Test Requirements

Maps each acceptance criterion from the design plan to specific tests, with test type, file location, owning phase/task, and verification details.

---

## AC1: JSON Download

### AC1.1 — Service downloads holdings JSON for a valid ETF ticker and as-of date

| Field | Value |
|-------|-------|
| **AC text** | Service downloads holdings JSON for a valid ETF ticker and as-of date |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceDownloadTests.cs` |
| **Phase/Task** | Phase 1, Task 7 |
| **Verifies** | Mock `HttpMessageHandler` returns 200 with valid iShares JSON body. Assert returned data is not null and contains expected `aaData` structure. |

### AC1.2 — BOM-prefixed responses are handled without parse errors

| Field | Value |
|-------|-------|
| **AC text** | BOM-prefixed responses are handled without parse errors |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceDownloadTests.cs` |
| **Phase/Task** | Phase 1, Task 7 |
| **Verifies** | Mock returns 200 with `\uFEFF` prefix prepended to valid JSON. Assert parsing succeeds without error. |

### AC1.3 — Unknown ETF ticker returns null/empty result (no exception)

| Field | Value |
|-------|-------|
| **AC text** | Unknown ETF ticker returns null/empty result (no exception) |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceDownloadTests.cs` |
| **Phase/Task** | Phase 1, Task 7 |
| **Verifies** | Call with an ETF ticker not in `ishares_etf_configs.json` (e.g., "ZZZZZ"). Assert returns null/empty, no exception thrown. |

### AC1.4 — Network timeout after 60s returns null/empty result with logged error

| Field | Value |
|-------|-------|
| **AC text** | Network timeout after 60s returns null/empty result with logged error |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceDownloadTests.cs` |
| **Phase/Task** | Phase 1, Task 7 |
| **Verifies** | Mock throws `TaskCanceledException` (simulating timeout). Assert returns null/empty, no exception propagated. |

### AC1.5 — Weekend as-of date is adjusted to last business day (Friday)

| Field | Value |
|-------|-------|
| **AC text** | Weekend as-of date is adjusted to last business day (Friday) |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceDownloadTests.cs` |
| **Phase/Task** | Phase 1, Task 7 |
| **Verifies** | Call with a Saturday date (e.g., `2025-01-25`). Assert the HTTP request URL contains `asOfDate=20250124` (Friday). |

---

## AC2: Holdings Parsing

### AC2.1 — Format A JSON (IVV-style, 17 cols) parses all equity holdings with correct weights

| Field | Value |
|-------|-------|
| **AC text** | Format A JSON (IVV-style, 17 cols) parses all equity holdings with correct weights |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceParsingTests.cs` |
| **Phase/Task** | Phase 1, Task 9 |
| **Verifies** | Parse Format A sample JSON (`TestData/format_a_sample.json`). Assert correct number of equity holdings returned. Assert first holding has correct ticker, name, sector, weight (divided by 100), market value, shares, CUSIP, ISIN. |

**Also verified by pipeline parity test:**

| Field | Value |
|-------|-------|
| **Test type** | Integration |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Integration/PipelineParityTests.cs` |
| **Phase/Task** | Phase 4, Task 2 |
| **Verifies** | `FormatA_ParseOutput_MatchesPythonPipeline` — load `format_a_sample.json`, parse with C#, assert equity count, field values, weight division, and market value extraction all match expected Python-equivalent output. |

### AC2.2 — Format B JSON (IJK-style, 19 cols) parses all equity holdings with correct weights

| Field | Value |
|-------|-------|
| **AC text** | Format B JSON (IJK-style, 19 cols) parses all equity holdings with correct weights |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceParsingTests.cs` |
| **Phase/Task** | Phase 1, Task 9 |
| **Verifies** | Parse Format B sample JSON (`TestData/format_b_sample.json`). Assert correct number of equity holdings returned. Assert weight comes from column index 17 (not 5). Assert sector comes from column index 3 (not 2). |

**Also verified by pipeline parity test:**

| Field | Value |
|-------|-------|
| **Test type** | Integration |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Integration/PipelineParityTests.cs` |
| **Phase/Task** | Phase 4, Task 2 |
| **Verifies** | `FormatB_ParseOutput_MatchesPythonPipeline` — load `format_b_sample.json`, parse with C#, assert column indices and field mapping match expected Python-equivalent output. |

### AC2.3 — Non-equity rows (Cash, Futures, Money Market) are filtered out

| Field | Value |
|-------|-------|
| **AC text** | Non-equity rows (Cash, Futures, Money Market) are filtered out |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceParsingTests.cs` |
| **Phase/Task** | Phase 1, Task 9 |
| **Verifies** | Both Format A and Format B samples include non-equity rows (Cash, Futures). Assert those rows are NOT in the returned holdings list. Assert count matches only equity rows. |

**Also verified by pipeline parity test:**

| Field | Value |
|-------|-------|
| **Test type** | Integration |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Integration/PipelineParityTests.cs` |
| **Phase/Task** | Phase 4, Task 2 |
| **Verifies** | `NonEquityFiltering_ExcludesSameRowsAsPython` — parse fixture containing Equity, Cash, Futures, Money Market, Cash Collateral and Margins. Assert only Equity rows remain, matching Python filter set: `{"Cash", "Cash Collateral and Margins", "Cash and/or Derivatives", "Futures", "Money Market"}`. |

### AC2.4 — Malformed JSON returns empty holdings list (no exception)

| Field | Value |
|-------|-------|
| **AC text** | Malformed JSON returns empty holdings list (no exception) |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceParsingTests.cs` |
| **Phase/Task** | Phase 1, Task 9 |
| **Verifies** | Pass malformed JSON string (e.g., `"not json"` or `"{}"` with no `aaData`). Assert returns empty list, no exception thrown. |

### AC2.5 — Holdings with missing weight or market value are included with null values

| Field | Value |
|-------|-------|
| **AC text** | Holdings with missing weight or market value are included with null values |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceParsingTests.cs` |
| **Phase/Task** | Phase 1, Task 9 |
| **Verifies** | Include a holding with `"-"` for weight and `"N/A"` for market value. Assert the returned holding has `Weight == null` and `MarketValue == null` but is still included in the list. |

**Also verified by pipeline parity test:**

| Field | Value |
|-------|-------|
| **Test type** | Integration |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Integration/PipelineParityTests.cs` |
| **Phase/Task** | Phase 4, Task 2 |
| **Verifies** | `WeightConversion_PercentageToDecimal_ConsistentWithPython` — assert `"-"` produces `null`, `0.0` produces `0m`, and known percentages are correctly divided by 100. |

---

## AC3: Database Persistence

### AC3.1 — New securities are created in SecurityMaster with correct fields

| Field | Value |
|-------|-------|
| **AC text** | New securities are created in SecurityMaster with correct fields |
| **Test type** | Unit (EF Core InMemory) |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServicePersistenceTests.cs` |
| **Phase/Task** | Phase 1, Task 11 |
| **Verifies** | Ingest an ETF where holdings have tickers not in SecurityMaster. Assert new `SecurityMasterEntity` rows created with correct IssueName, TickerSymbol, Exchange, SecurityType, Country, Currency, Isin, IsActive. |

### AC3.2 — Existing securities are matched by ticker, then CUSIP, then ISIN (3-level lookup)

| Field | Value |
|-------|-------|
| **AC text** | Existing securities are matched by ticker, then CUSIP, then ISIN (3-level lookup) |
| **Test type** | Unit (EF Core InMemory) |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServicePersistenceTests.cs` |
| **Phase/Task** | Phase 1, Task 11 |
| **Verifies** | Pre-seed SecurityMaster with a security by ticker. Pre-seed SecurityIdentifier with a CUSIP entry for a different security. Pre-seed SecurityIdentifier with an ISIN entry for a third security. Ingest holdings that match each level. Assert each holding matched the correct SecurityAlias (level 1 by ticker, level 2 by CUSIP, level 3 by ISIN). |

### AC3.3 — SecurityIdentifier rows are upserted; changed values trigger SCD Type 2 history snapshot

| Field | Value |
|-------|-------|
| **AC text** | SecurityIdentifier rows are upserted; changed values trigger SCD Type 2 history snapshot |
| **Test type** | Unit (EF Core InMemory) |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServicePersistenceTests.cs` |
| **Phase/Task** | Phase 1, Task 11 |
| **Verifies** | Pre-seed SecurityIdentifier with SecurityAlias=1, IdentifierType="CUSIP", IdentifierValue="OLD_CUSIP". Ingest a holding for SecurityAlias=1 with a DIFFERENT CUSIP. Assert SecurityIdentifierHist row created with old value and date range. Assert SecurityIdentifier row updated to new value. |

### AC3.4 — IndexConstituent records are inserted with correct Weight, MarketValue, Shares, Sector, SourceId

| Field | Value |
|-------|-------|
| **AC text** | IndexConstituent records are inserted with correct Weight, MarketValue, Shares, Sector, SourceId |
| **Test type** | Unit (EF Core InMemory) |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServicePersistenceTests.cs` |
| **Phase/Task** | Phase 1, Task 11 |
| **Verifies** | Ingest a holding with known Weight, MarketValue, Shares, Sector. Query IndexConstituent after ingestion. Assert all fields match expected values, SourceId=10, SourceTicker matches holding ticker. |

### AC3.5 — Duplicate constituent inserts are skipped idempotently

| Field | Value |
|-------|-------|
| **AC text** | Duplicate constituent inserts (same IndexId + SecurityAlias + EffectiveDate + SourceId) are skipped idempotently |
| **Test type** | Unit (EF Core InMemory) |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServicePersistenceTests.cs` |
| **Phase/Task** | Phase 1, Task 11 |
| **Verifies** | Ingest the same ETF + date twice. Assert IndexConstituent count after second run equals count after first run (no duplicates). Assert stats show `skippedExisting > 0` on second run. |

**Note:** EF Core InMemory provider does not enforce unique constraints. This test validates the application-level duplicate check (`AnyAsync` guard before insert), not the database-level `IX_IndexConstituent_Unique` composite index. The database constraint serves as a safety net in production but cannot be verified in InMemory tests.

### AC3.6 — DB write failure for one holding does not abort the entire ETF

| Field | Value |
|-------|-------|
| **AC text** | DB write failure for one holding does not abort the entire ETF — remaining holdings are processed |
| **Test type** | Unit (EF Core InMemory) |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServicePersistenceTests.cs` |
| **Phase/Task** | Phase 1, Task 11 |
| **Verifies** | Create a scenario where one holding causes a SaveChanges failure (e.g., by pre-seeding conflicting data or using a mock that throws on specific input). Assert the service continues processing remaining holdings. Assert `stats.Failed > 0` and `stats.Inserted > 0` (other holdings succeeded). |

---

## AC4: Index Manager Tab

### AC4.1 — "Load All" button iterates all configured ETFs with visible progress

| Field | Value |
|-------|-------|
| **AC text** | "Load All" button iterates all configured ETFs with visible progress (current ETF / total, holdings count) |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/IndexManagerViewModelTests.cs` |
| **Phase/Task** | Phase 2, Task 2 |
| **Verifies** | Call `LoadAllCommand` with no specific ETF selected. Assert `IngestAllEtfsAsync` was called on the mock service. Fire mock `ProgressUpdated` events and assert `CurrentEtfLabel`, `Progress`, `ProgressText` properties update correctly. |

**Also requires manual verification** (see Manual Verification section below).

### AC4.2 — Single-ETF override allows loading one specific ETF

| Field | Value |
|-------|-------|
| **AC text** | Single-ETF override allows loading one specific ETF |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/IndexManagerViewModelTests.cs` |
| **Phase/Task** | Phase 2, Task 2 |
| **Verifies** | Set `SelectedEtfTicker` to "IVV". Call `LoadAllCommand`. Assert `IngestEtfAsync` was called with "IVV" (not `IngestAllEtfsAsync`). |

### AC4.3 — As-of date defaults to last month-end; can be changed by user

| Field | Value |
|-------|-------|
| **AC text** | As-of date defaults to last month-end; can be changed by user |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/IndexManagerViewModelTests.cs` |
| **Phase/Task** | Phase 2, Task 2 |
| **Verifies** | Assert `AsOfDate` defaults to last business day of previous month. Change `AsOfDate` to a specific date, call `LoadAllCommand`, assert service was called with the changed date. |

### AC4.4 — Activity log shows per-ETF results

| Field | Value |
|-------|-------|
| **AC text** | Activity log shows per-ETF results (parsed count, matched, created, inserted, skipped) |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/IndexManagerViewModelTests.cs` |
| **Phase/Task** | Phase 2, Task 2 |
| **Verifies** | Fire mock `LogMessage` events during load. Assert messages appear in `LogMessages` collection in newest-first order. |

### AC4.5 — Cancel button stops the loading loop after current ETF completes

| Field | Value |
|-------|-------|
| **AC text** | Cancel button stops the loading loop after current ETF completes |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/IndexManagerViewModelTests.cs` |
| **Phase/Task** | Phase 2, Task 2 |
| **Verifies** | Start a load, then call `CancelCommand`. Assert the CancellationToken passed to the service is cancelled. |

### AC4.6 — ETF download failure is logged and skipped; loading continues with next ETF

| Field | Value |
|-------|-------|
| **AC text** | ETF download failure is logged and skipped; loading continues with next ETF |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/IndexManagerViewModelTests.cs` |
| **Phase/Task** | Phase 2, Task 2 |
| **Verifies** | Configure mock to throw on a specific ETF during `IngestAllEtfsAsync`. Assert the ViewModel does not crash, `IsLoading` returns to false, and the error is logged to `LogMessages`. |

---

## AC5: Crawler Integration

### AC5.1 — Crawl start with stale constituent data triggers auto-loading before gap filling

| Field | Value |
|-------|-------|
| **AC text** | Crawl start with stale constituent data triggers auto-loading before gap filling |
| **Test type** | Unit (staleness detection) + Unit (crawler integration) |
| **Test files** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceStalenessTests.cs`, `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/CrawlerViewModelConstituentTests.cs` |
| **Phase/Task** | Phase 3, Task 2 (staleness) + Phase 3, Task 4 (crawler) |
| **Verifies** | **Staleness test:** Pre-seed IndexDefinition for "SP500" with ProxyEtfTicker="IVV". Pre-seed IndexConstituent with max EffectiveDate = two months ago. Call `GetStaleEtfsAsync()`. Assert result contains ("IVV", "SP500"). **Crawler test:** Mock `GetStaleEtfsAsync` to return 2 stale ETFs. Mock `IngestEtfAsync` to return successful stats. Assert `IngestEtfAsync` was called for each stale ETF. Assert `GetStaleEtfsAsync` was called exactly once. |

### AC5.2 — Crawl start with up-to-date constituents skips constituent loading silently

| Field | Value |
|-------|-------|
| **AC text** | Crawl start with up-to-date constituents skips constituent loading silently |
| **Test type** | Unit (staleness detection) + Unit (crawler integration) |
| **Test files** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceStalenessTests.cs`, `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/CrawlerViewModelConstituentTests.cs` |
| **Phase/Task** | Phase 3, Task 2 (staleness) + Phase 3, Task 4 (crawler) |
| **Verifies** | **Staleness test:** Pre-seed IndexDefinition for "SP500". Pre-seed IndexConstituent with EffectiveDate = last month-end. Call `GetStaleEtfsAsync()`. Assert result is empty. **Crawler test:** Mock `GetStaleEtfsAsync` to return empty list. Assert `IngestEtfAsync` was NOT called. Assert no error was logged. |

### AC5.3 — Status text indicates "Loading constituents..." during auto-refresh

| Field | Value |
|-------|-------|
| **AC text** | Status text indicates "Loading constituents..." during auto-refresh |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/CrawlerViewModelConstituentTests.cs` |
| **Phase/Task** | Phase 3, Task 4 |
| **Verifies** | Mock `GetStaleEtfsAsync` to return stale ETFs. Capture all status text changes (subscribe to PropertyChanged). Assert status text included "Loading constituents" or "Checking constituent" at some point. |

### AC5.4 — If all ETFs fail during auto-refresh, crawler proceeds to gap filling anyway (best effort)

| Field | Value |
|-------|-------|
| **AC text** | If all ETFs fail during auto-refresh, crawler proceeds to gap filling anyway (best effort) |
| **Test type** | Unit |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/CrawlerViewModelConstituentTests.cs` |
| **Phase/Task** | Phase 3, Task 4 |
| **Verifies** | Mock `GetStaleEtfsAsync` to throw an exception. Assert the ViewModel does NOT crash. Assert `IsCrawling` eventually proceeds (the crawl timer would start if gaps exist). Assert the error was logged to activity. |

---

## AC6: Cross-Cutting

### AC6.1 — Rate limiting enforces minimum 2s between iShares HTTP requests

| Field | Value |
|-------|-------|
| **AC text** | Rate limiting enforces minimum 2s between iShares HTTP requests |
| **Test type** | Integration (slow, timing-based) |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Integration/RateLimitingTests.cs` |
| **Phase/Task** | Phase 4, Task 1 |
| **Verifies** | Two tests: (1) `IngestAllEtfsAsync_EnforcesMinimum2sDelayBetweenRequests` — real service with mock HTTP handler returning empty JSON for 3 configured ETFs, records HTTP request timestamps, asserts >= 1.9s gap between consecutive pairs. (2) `CrawlerConstituentPreStep_EnforcesMinimum2sDelayBetweenRequests` — mocked service returning 3 stale ETFs, records `IngestEtfAsync` invocation timestamps, asserts >= 1.9s gap. Tests marked `[Trait("Category", "Slow")]` (~12-15s total runtime). |

### AC6.2 — C# output matches Python pipeline output for IVV and IJK

| Field | Value |
|-------|-------|
| **AC text** | C# output matches Python pipeline output for IVV and IJK (row counts, weight values within rounding tolerance) |
| **Test type** | Integration |
| **Test file** | `projects/eodhd-loader/tests/EodhdLoader.Tests/Integration/PipelineParityTests.cs` |
| **Phase/Task** | Phase 4, Task 2 |
| **Verifies** | Four tests: (1) `FormatA_ParseOutput_MatchesPythonPipeline` — equity count, field values, weight division, market value extraction. (2) `FormatB_ParseOutput_MatchesPythonPipeline` — correct column indices for Format B. (3) `WeightConversion_PercentageToDecimal_ConsistentWithPython` — `6.5432` becomes `0.065432m`, `"-"` becomes `null`, `0.0` becomes `0m`. (4) `NonEquityFiltering_ExcludesSameRowsAsPython` — exact filter set matches Python: `{"Cash", "Cash Collateral and Margins", "Cash and/or Derivatives", "Futures", "Money Market"}`. |

### AC6.3 — No references to Wikipedia scraper remain in codebase after refactor

| Field | Value |
|-------|-------|
| **AC text** | No references to Wikipedia scraper remain in codebase after refactor |
| **Test type** | Manual (automated scan) |
| **Test file** | None (grep-based verification) |
| **Phase/Task** | Phase 4, Task 3 |
| **Verifies** | Four grep searches across `projects/eodhd-loader/src/` for `*.cs` and `*.xaml` files: (1) `wikipedia` (case-insensitive), (2) `IndexService`, (3) `IndexConstituentsResponse`, (4) `en.wikipedia.org`. All four must return zero matches. Build must succeed after any removals. |

### AC6.4 — App builds and runs with new service registered in DI

| Field | Value |
|-------|-------|
| **AC text** | App builds and runs with new service registered in DI |
| **Test type** | Manual (build + launch) |
| **Test file** | None (build and runtime verification) |
| **Phase/Task** | Phase 4, Task 4 |
| **Verifies** | (1) `dotnet build projects/eodhd-loader/EodhdLoader.sln -c Release --no-incremental` succeeds with zero errors. (2) `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/` — all tests pass. (3) `dotnet run --project projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj -c Release` — app window appears without DI-related exceptions. (4) Manual inspection that `IISharesConstituentService`, `IndexManagerViewModel`, and `CrawlerViewModel` are all correctly wired in `App.xaml.cs`. |

---

## Manual Verification Requirements

The following acceptance criteria require human verification because they involve visual UI behavior, real network interaction, or runtime observation that cannot be fully captured in automated tests.

### AC4.1 — Visual Progress Display (partial)

**Why it cannot be fully automated:** The unit test verifies that ViewModel properties update correctly when mock events fire, but it cannot verify that the WPF controls (ProgressBar, TextBlock) render correctly, animate smoothly, or remain responsive during a long-running load of 277 ETFs.

**Manual verification approach:**
1. Launch the app and navigate to the iShares Loader tab
2. Click "Load" with "(All)" selected
3. Observe the progress bar advancing and the current ETF label updating (e.g., "Loading IVV (3 / 277)...")
4. Verify the UI remains responsive (window can be moved/resized during loading)

**Expected behavior:**
- Progress bar fills from 0% to 100% over approximately 9.2 minutes
- Current ETF label updates after each ETF completes
- Per-ETF stats appear in the activity log in real time
- No UI freezes or unresponsive window warnings

### AC4.3 — DatePicker Interaction (partial)

**Why it cannot be fully automated:** The unit test verifies the default date value and that changed dates propagate to the service. It cannot verify that the WPF DatePicker control renders correctly or that the user can select a date via the calendar popup.

**Manual verification approach:**
1. Launch the app and navigate to the iShares Loader tab
2. Verify the as-of date field shows the last business day of the previous month
3. Click the DatePicker, select a different date, click "Load"
4. Verify the activity log shows the selected date being used

**Expected behavior:**
- DatePicker defaults to last business day of previous month (e.g., 2026-01-30 if today is February)
- Calendar popup works correctly
- Selected date is passed through to the service

### AC5.3 — Crawler Status Text Display

**Why it cannot be fully automated:** The unit test captures PropertyChanged events, but verifying the actual status text rendering in the Crawler tab's UI requires visual inspection of the running application.

**Manual verification approach:**
1. Ensure constituent data is stale (or delete recent IndexConstituent rows for one index)
2. Launch the app and start a crawl
3. Watch the Crawler tab's status area during startup

**Expected behavior:**
- Status text shows "Checking constituent data freshness..." briefly
- If stale ETFs found, shows "Loading constituents for N stale ETFs..."
- After completion, shows summary (e.g., "Constituent refresh complete: 3 loaded, 0 failed")
- Crawler then proceeds to normal gap filling

### AC6.1 — Real Network Rate Limiting (partial)

**Why it cannot be fully automated:** The integration tests verify timing with mock HTTP handlers. Real-world rate limiting verification requires observing actual HTTP requests to `ishares.com` with real network latency.

**Manual verification approach:**
1. Launch the app, navigate to iShares Loader tab
2. Select a single ETF (e.g., "IVV") and load it
3. Then select "(All)" and load all ETFs
4. Watch the activity log timestamps

**Expected behavior:**
- Activity log entries for consecutive ETFs are spaced at least 2 seconds apart
- No HTTP 429 (rate limit) errors appear in the log
- Full load of 277 ETFs takes approximately 9.2 minutes

### AC6.2 — Real Data Pipeline Parity (partial)

**Why it cannot be fully automated:** The integration tests use synthetic fixture data. Verifying against real iShares data requires comparing live C# output against a Python pipeline run on the same as-of date.

**Manual verification approach:**
1. Run Python pipeline: `python helpers/ishares_ingest.py` for IVV and IJK on a specific date
2. Note row counts, total weight sums, and sample security matches
3. Run C# loader for the same ETFs and same as-of date
4. Compare row counts, total weights (within 0.0001 tolerance), and security matches

**Expected behavior:**
- Identical equity row counts for IVV and IJK
- Weight sums match within rounding tolerance
- Same securities matched/created in both pipelines
- Same non-equity rows excluded

### AC6.4 — Runtime DI Validation (partial)

**Why it cannot be fully automated:** The build verifies type compatibility, but runtime DI resolution (including correct scoping of `StockAnalyzerDbContext` and transient service lifetime) requires launching the application.

**Manual verification approach:**
1. Build and launch the application
2. Navigate to iShares Loader tab (exercises IndexManagerViewModel DI)
3. Navigate to Crawler tab and start a crawl (exercises CrawlerViewModel DI)
4. Check for any unhandled exception dialogs or crash logs

**Expected behavior:**
- App launches without exceptions
- Both tabs load their ViewModels without DI resolution errors
- Loading an ETF completes without null reference errors from missing dependencies

---

## Test File Summary

| Test File | Phase | Task | ACs Covered | Test Type | Trait |
|-----------|-------|------|-------------|-----------|-------|
| `Services/ISharesConstituentServiceDownloadTests.cs` | 1 | 7 | AC1.1-AC1.5 | Unit | — |
| `Services/ISharesConstituentServiceParsingTests.cs` | 1 | 9 | AC2.1-AC2.5 | Unit | — |
| `TestData/format_a_sample.json` | 1 | 9 | AC2.1, AC2.3, AC2.5 | Fixture | — |
| `TestData/format_b_sample.json` | 1 | 9 | AC2.2, AC2.3 | Fixture | — |
| `Services/ISharesConstituentServicePersistenceTests.cs` | 1 | 11 | AC3.1-AC3.6 | Unit (InMemory) | — |
| `ViewModels/IndexManagerViewModelTests.cs` | 2 | 2 | AC4.1-AC4.6 | Unit | — |
| `Services/ISharesConstituentServiceStalenessTests.cs` | 3 | 2 | AC5.1, AC5.2 | Unit (InMemory) | — |
| `ViewModels/CrawlerViewModelConstituentTests.cs` | 3 | 4 | AC5.1-AC5.4 | Unit | — |
| `Integration/RateLimitingTests.cs` | 4 | 1 | AC6.1 | Integration | `Slow` |
| `Integration/PipelineParityTests.cs` | 4 | 2 | AC6.2 | Integration | — |

All test file paths are relative to `projects/eodhd-loader/tests/EodhdLoader.Tests/`.

---

## Coverage Matrix

| AC | Unit Test | Integration Test | Manual Verification | Notes |
|----|-----------|-----------------|-------------------|-------|
| AC1.1 | DownloadTests | — | — | |
| AC1.2 | DownloadTests | — | — | |
| AC1.3 | DownloadTests | — | — | |
| AC1.4 | DownloadTests | — | — | |
| AC1.5 | DownloadTests | — | — | |
| AC2.1 | ParsingTests | PipelineParityTests | — | |
| AC2.2 | ParsingTests | PipelineParityTests | — | |
| AC2.3 | ParsingTests | PipelineParityTests | — | |
| AC2.4 | ParsingTests | — | — | |
| AC2.5 | ParsingTests | PipelineParityTests | — | |
| AC3.1 | PersistenceTests | — | — | |
| AC3.2 | PersistenceTests | — | — | |
| AC3.3 | PersistenceTests | — | — | |
| AC3.4 | PersistenceTests | — | — | |
| AC3.5 | PersistenceTests | — | — | InMemory does not enforce unique constraints |
| AC3.6 | PersistenceTests | — | — | |
| AC4.1 | IndexManagerVMTests | — | Visual progress display | |
| AC4.2 | IndexManagerVMTests | — | — | |
| AC4.3 | IndexManagerVMTests | — | DatePicker interaction | |
| AC4.4 | IndexManagerVMTests | — | — | |
| AC4.5 | IndexManagerVMTests | — | — | |
| AC4.6 | IndexManagerVMTests | — | — | |
| AC5.1 | StalenessTests + CrawlerTests | — | — | |
| AC5.2 | StalenessTests + CrawlerTests | — | — | |
| AC5.3 | CrawlerTests | — | Crawler status text display | |
| AC5.4 | CrawlerTests | — | — | |
| AC6.1 | — | RateLimitingTests | Real network rate limiting | Slow tests (~12-15s) |
| AC6.2 | — | PipelineParityTests | Real data parity | |
| AC6.3 | — | — | Grep scan (automated) | No test file; verification via shell commands |
| AC6.4 | — | — | Build + launch | No test file; verified by build and app startup |
