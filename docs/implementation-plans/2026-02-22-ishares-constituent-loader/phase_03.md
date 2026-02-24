# iShares Constituent Loader — Phase 3: Crawler Integration

**Goal:** Crawler automatically checks for stale constituent data at crawl start and loads missing month-end snapshots before proceeding with price gap filling.

**Architecture:** Add `IISharesConstituentService` as a dependency to `CrawlerViewModel`. Insert a new pre-step in `StartCrawlAsync()` — after the initial `RefreshGapsAsync()` succeeds but before `PromoteAndRefreshAsync()`. The pre-step calls `GetStaleEtfsAsync()` to identify ETFs missing the latest month-end, then loads them via `IngestEtfAsync()` with 2-second pacing. If all ETFs fail, the crawler proceeds anyway (best effort).

**Tech Stack:** C# / WPF / CommunityToolkit.Mvvm, EF Core LINQ queries

**Scope:** 4 phases from original design (this is phase 3 of 4)

**Codebase verified:** 2026-02-22

---

## Acceptance Criteria Coverage

This phase implements and tests:

### ishares-constituent-loader.AC5: Crawler Integration
- **ishares-constituent-loader.AC5.1 Success:** Crawl start with stale constituent data triggers auto-loading before gap filling
- **ishares-constituent-loader.AC5.2 Success:** Crawl start with up-to-date constituents skips constituent loading silently
- **ishares-constituent-loader.AC5.3 Success:** Status text indicates "Loading constituents..." during auto-refresh
- **ishares-constituent-loader.AC5.4 Edge:** If all ETFs fail during auto-refresh, crawler proceeds to gap filling anyway (best effort)

---

## Reference Files

The executor should read these files for context:

- **CrawlerViewModel:** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/ViewModels/CrawlerViewModel.cs`
  - Constructor: lines 191-201 (inject IISharesConstituentService here)
  - StartCrawlAsync(): lines 330-397 (insert pre-step after line 357)
  - Status properties: CurrentPhase (line 50), CurrentAction (line 69), StatusText (line 44)
  - AddActivity(): lines 1090-1108 (activity log pattern)
  - Cancellation: _cts created at line 333, checked at line 485
- **IISharesConstituentService (from Phase 1):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/Services/IISharesConstituentService.cs`
- **App.xaml.cs:** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/App.xaml.cs` (no changes needed — DI auto-resolves)

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->
## Subcomponent A: GetStaleEtfsAsync Implementation

<!-- START_TASK_1 -->
### Task 1: Implement GetStaleEtfsAsync in ISharesConstituentService

**Verifies:** ishares-constituent-loader.AC5.1, ishares-constituent-loader.AC5.2

**Files:**
- Modify: `projects/eodhd-loader/src/EodhdLoader/Services/ISharesConstituentService.cs`

**Implementation:**

Implement the `GetStaleEtfsAsync()` method declared in the interface (Phase 1). This method queries the database to determine which ETFs are missing the latest month-end constituent data.

Logic:
1. Calculate the last month-end business day (same `GetLastMonthEnd()` logic from Phase 2 ViewModel, or share a static utility)
2. Query `IndexDefinition` table for all active index definitions that have a `ProxyEtfTicker` (these are the ETFs we track)
3. For each `IndexDefinition`, query `IndexConstituent` for the max `EffectiveDate` where `SourceId = 10` (iShares)
4. If max `EffectiveDate` is null or earlier than the last month-end → ETF is stale
5. Return list of `(EtfTicker, IndexCode)` tuples for stale ETFs

```csharp
public async Task<IReadOnlyList<(string EtfTicker, string IndexCode)>> GetStaleEtfsAsync(CancellationToken ct = default)
{
    var lastMonthEnd = GetLastMonthEnd();
    var staleEtfs = new List<(string, string)>();

    var indexDefs = await _dbContext.IndexDefinitions
        .Where(id => id.ProxyEtfTicker != null)
        .ToListAsync(ct);

    foreach (var indexDef in indexDefs)
    {
        var maxDate = await _dbContext.IndexConstituents
            .Where(ic => ic.IndexId == indexDef.IndexId && ic.SourceId == ISharesSourceId)
            .MaxAsync(ic => (DateTime?)ic.EffectiveDate, ct);

        if (maxDate == null || maxDate.Value.Date < lastMonthEnd.Date)
        {
            // Look up the ETF ticker from our config that matches this index
            var etfEntry = EtfConfigs.FirstOrDefault(kvp => kvp.Value.IndexCode == indexDef.IndexCode);
            if (etfEntry.Key != null)
                staleEtfs.Add((etfEntry.Key, indexDef.IndexCode));
        }
    }

    return staleEtfs;
}
```

Note: This only checks the 7 seeded benchmark indices (those with `ProxyEtfTicker` in `IndexDefinition`). The full 277 ETFs in `ishares_etf_configs.json` may not all have `IndexDefinition` entries. The staleness check is conservative — it only checks indices that are explicitly tracked.

**Verification:**
Run: `dotnet build projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
Expected: Build succeeds

**Commit:** `feat(eodhd-loader): implement GetStaleEtfsAsync for constituent staleness detection`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Tests for GetStaleEtfsAsync

**Verifies:** ishares-constituent-loader.AC5.1, ishares-constituent-loader.AC5.2

**Files:**
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceStalenessTests.cs`

**Testing:**

Use EF Core InMemory provider. Pre-seed with IndexDefinition entries and varying IndexConstituent data.

Tests must verify each AC listed above:

- **ishares-constituent-loader.AC5.1 (stale data detected):** Pre-seed IndexDefinition for "SP500" with ProxyEtfTicker="IVV". Pre-seed IndexConstituent with max EffectiveDate = two months ago. Call `GetStaleEtfsAsync()`. Assert result contains ("IVV", "SP500").
- **ishares-constituent-loader.AC5.2 (up-to-date data):** Pre-seed IndexDefinition for "SP500". Pre-seed IndexConstituent with EffectiveDate = last month-end. Call `GetStaleEtfsAsync()`. Assert result is empty.
- **Mixed staleness:** Pre-seed two IndexDefinitions — one stale, one current. Assert only the stale one is returned.
- **No constituent data at all:** Pre-seed IndexDefinition but NO IndexConstituent rows. Assert the ETF is returned as stale (null max date).

**Verification:**
Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/ --filter "FullyQualifiedName~StalenessTests"`
Expected: All tests pass

**Commit:** `test(eodhd-loader): add staleness detection tests for AC5.1, AC5.2`
<!-- END_TASK_2 -->
<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 3-4) -->
## Subcomponent B: CrawlerViewModel Integration

<!-- START_TASK_3 -->
### Task 3: Add Constituent Pre-Step to CrawlerViewModel

**Verifies:** ishares-constituent-loader.AC5.1, ishares-constituent-loader.AC5.3, ishares-constituent-loader.AC5.4

**Files:**
- Modify: `projects/eodhd-loader/src/EodhdLoader/ViewModels/CrawlerViewModel.cs`

**Implementation:**

**Step 1: Add service dependency to constructor**

Add `IISharesConstituentService` as a second constructor parameter:
```csharp
public CrawlerViewModel(StockAnalyzerApiClient apiClient, IISharesConstituentService constituentService)
{
    _apiClient = apiClient;
    _constituentService = constituentService;
    // ... rest of existing init
}
```

Add field: `private readonly IISharesConstituentService _constituentService;`

**Step 2: Create CheckAndLoadConstituentsAsync method**

```csharp
private async Task CheckAndLoadConstituentsAsync()
{
    CurrentAction = "Checking constituent staleness...";
    StatusText = "Checking constituent data freshness...";
    AddActivity("🔍", "Constituents", "Checking for stale month-end data...");

    try
    {
        var staleEtfs = await _constituentService.GetStaleEtfsAsync(_cts?.Token ?? default);

        if (staleEtfs.Count == 0)
        {
            AddActivity("✅", "Constituents", "All constituent data is current");
            return;
        }

        AddActivity("📊", "Constituents", $"Found {staleEtfs.Count} ETFs with stale data, loading...");
        StatusText = $"Loading constituents for {staleEtfs.Count} stale ETFs...";

        int loaded = 0, failed = 0;
        foreach (var (etfTicker, indexCode) in staleEtfs)
        {
            if (_cts?.Token.IsCancellationRequested == true) break;

            CurrentAction = $"Loading constituents: {etfTicker} ({loaded + failed + 1}/{staleEtfs.Count})";

            try
            {
                var stats = await _constituentService.IngestEtfAsync(etfTicker, null, _cts?.Token ?? default);
                loaded++;
                AddActivity("✅", etfTicker, $"{stats.Inserted} inserted, {stats.SkippedExisting} skipped");
            }
            catch (Exception ex)
            {
                failed++;
                AddActivity("⚠️", etfTicker, $"Failed: {ex.Message}");
            }

            // Rate limiting — use shared constant from service (AC6.1)
            if (_cts?.Token.IsCancellationRequested != true)
                await Task.Delay(ISharesConstituentService.RequestDelayMs, _cts?.Token ?? default);
        }

        var summary = $"Constituent refresh complete: {loaded} loaded, {failed} failed";
        AddActivity("📊", "Constituents", summary);
        StatusText = summary;
    }
    catch (OperationCanceledException)
    {
        AddActivity("⏹️", "Constituents", "Constituent check cancelled");
    }
    catch (Exception ex)
    {
        // Best effort — log and continue to gap filling (AC5.4)
        AddActivity("⚠️", "Constituents", $"Staleness check failed: {ex.Message}");
        StatusText = "Constituent check failed — proceeding to gap filling";
    }
}
```

**Step 3: Insert call in StartCrawlAsync**

Insert the call after `RefreshGapsAsync()` succeeds (after line 357) but before the `_securityQueue.Count == 0` check (line 366):

```csharp
// After RefreshGapsAsync succeeds:
await CheckAndLoadConstituentsAsync();

// Then continue with existing PromoteAndRefreshAsync logic...
```

Key behaviors:
- If stale ETFs found → loads them with 2s pacing, updates status/activity
- If no stale ETFs → logs "current" and continues silently (AC5.2)
- If all fail → catches exception, logs, continues to gap filling (AC5.4)
- If cancelled → breaks out of loop, continues to gap filling

**Verification:**
Run: `dotnet build projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
Expected: Build succeeds

**Commit:** `feat(eodhd-loader): add constituent staleness pre-step to Crawler startup`
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Tests for Crawler Constituent Integration

**Verifies:** ishares-constituent-loader.AC5.1, ishares-constituent-loader.AC5.2, ishares-constituent-loader.AC5.3, ishares-constituent-loader.AC5.4

**Files:**
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/CrawlerViewModelConstituentTests.cs`

**Testing:**

Use `Mock<IISharesConstituentService>` and `Mock<StockAnalyzerApiClient>`. Focus on testing the `CheckAndLoadConstituentsAsync` flow as invoked via `StartCrawlAsync`.

Note: Testing the full `StartCrawlAsync` requires mocking `StockAnalyzerApiClient.GetPriceGapsAsync` to return a valid response (so `RefreshGapsAsync` succeeds). Set up a basic mock that returns an empty gaps response.

Tests must verify each AC listed above:

- **ishares-constituent-loader.AC5.1:** Mock `GetStaleEtfsAsync` to return 2 stale ETFs. Mock `IngestEtfAsync` to return successful stats. Call `StartCrawlAsync` (via reflection or by making the method testable). Assert `IngestEtfAsync` was called for each stale ETF. Assert `GetStaleEtfsAsync` was called exactly once.
- **ishares-constituent-loader.AC5.2:** Mock `GetStaleEtfsAsync` to return empty list. Call `StartCrawlAsync`. Assert `IngestEtfAsync` was NOT called. Assert no error was logged.
- **ishares-constituent-loader.AC5.3:** Mock `GetStaleEtfsAsync` to return stale ETFs. Capture all status text changes (subscribe to PropertyChanged). Assert status text included "Loading constituents" or "Checking constituent" at some point.
- **ishares-constituent-loader.AC5.4:** Mock `GetStaleEtfsAsync` to throw an exception. Assert the ViewModel does NOT crash. Assert `IsCrawling` eventually proceeds (the crawl timer would start if gaps exist). Assert the error was logged to activity.

**Verification:**
Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/ --filter "FullyQualifiedName~CrawlerViewModelConstituentTests"`
Expected: All tests pass

**Commit:** `test(eodhd-loader): add Crawler constituent integration tests for AC5`
<!-- END_TASK_4 -->
<!-- END_SUBCOMPONENT_B -->
