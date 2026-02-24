# iShares Constituent Loader — Phase 2: Index Manager Tab Refactor

**Goal:** Replace the Wikipedia-based Index Manager UI with iShares constituent loading controls that leverage the `ISharesConstituentService` from Phase 1.

**Architecture:** Refactor `IndexManagerViewModel` to depend on `IISharesConstituentService` instead of `IndexService`. Replace ComboBox-based single-index selection with "Load All" button + optional single-ETF override. Replace date range pickers with a single as-of date defaulting to last month-end. Wire service progress/log events to the ViewModel's observable collections.

**Tech Stack:** C# / WPF / CommunityToolkit.Mvvm (ObservableProperty, RelayCommand), XAML data binding

**Scope:** 4 phases from original design (this is phase 2 of 4)

**Codebase verified:** 2026-02-22

---

## Acceptance Criteria Coverage

This phase implements and tests:

### ishares-constituent-loader.AC4: Index Manager Tab
- **ishares-constituent-loader.AC4.1 Success:** "Load All" button iterates all configured ETFs with visible progress (current ETF / total, holdings count)
- **ishares-constituent-loader.AC4.2 Success:** Single-ETF override allows loading one specific ETF
- **ishares-constituent-loader.AC4.3 Success:** As-of date defaults to last month-end; can be changed by user
- **ishares-constituent-loader.AC4.4 Success:** Activity log shows per-ETF results (parsed count, matched, created, inserted, skipped)
- **ishares-constituent-loader.AC4.5 Success:** Cancel button stops the loading loop after current ETF completes
- **ishares-constituent-loader.AC4.6 Failure:** ETF download failure is logged and skipped; loading continues with next ETF

---

## Reference Files

The executor should read these files for context:

- **Current IndexManagerViewModel:** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/ViewModels/IndexManagerViewModel.cs` (266 lines, full rewrite)
- **Current IndexManagerView.xaml:** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/Views/IndexManagerView.xaml` (114 lines, full rewrite)
- **IndexService to remove:** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/Services/IndexService.cs` (247 lines)
- **App.xaml.cs (DI):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/App.xaml.cs`
- **ViewModelBase pattern:** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/ViewModels/ViewModelBase.cs`
- **MainWindow.xaml (tab wiring):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/MainWindow.xaml`
- **MainViewModel (property):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/ViewModels/MainViewModel.cs`
- **IISharesConstituentService (from Phase 1):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/Services/IISharesConstituentService.cs`
- **IngestProgress model (from Phase 1):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/Models/IngestProgress.cs`

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->
## Subcomponent A: ViewModel Refactor

<!-- START_TASK_1 -->
### Task 1: Rewrite IndexManagerViewModel

**Verifies:** ishares-constituent-loader.AC4.1, ishares-constituent-loader.AC4.2, ishares-constituent-loader.AC4.3, ishares-constituent-loader.AC4.4, ishares-constituent-loader.AC4.5, ishares-constituent-loader.AC4.6

**Files:**
- Modify: `projects/eodhd-loader/src/EodhdLoader/ViewModels/IndexManagerViewModel.cs` (full rewrite)

**Implementation:**

Replace the entire ViewModel. The new version depends on `IISharesConstituentService` (from Phase 1) instead of `IndexService` + `StockAnalyzerApiClient`.

**Constructor dependencies:**
- `IISharesConstituentService constituentService` — the new service
- `ConfigurationService config` — retained for environment info
- Remove: `IndexService`, `StockAnalyzerApiClient`

**Observable properties to ADD:**
- `AsOfDate` (DateTime) — defaults to last business day of previous month. Use same `AdjustToLastBusinessDay` logic from Phase 1 service, applied to last day of previous calendar month.
- `SelectedEtfTicker` (string?) — null means "Load All", non-null means single-ETF override
- `AvailableEtfTickers` (ObservableCollection<string>) — populated from `constituentService.EtfConfigs.Keys`, sorted. First entry should be "(All)" sentinel.
- `CurrentEtfLabel` (string) — e.g., "Loading IVV (3 / 277)..."
- `TotalEtfsToLoad` (int) — total ETFs in current batch
- `CurrentEtfIndex` (int) — 1-based index of current ETF

**Observable properties to KEEP (with modified behavior):**
- `Progress` (double, 0-100) — now tracks ETF-level progress (currentEtf/totalEtfs * 100)
- `ProgressText` (string) — shows current ETF and stats
- `IsLoading` (bool) — true during Load All / single-ETF load
- `LogMessages` (ObservableCollection<string>) — wired to service's `LogMessage` event

**Observable properties to REMOVE:**
- `SelectedEnvironment`, `SelectedIndex`, `BackfillFromDate`, `BackfillToDate`, `ConstituentCount`, `ProcessedCount`, `ErrorCount`, `IsLoadingConstituents`, `AvailableIndices`, `Constituents`, `Environments`

**RelayCommand methods:**

1. `LoadAllCommand` → `LoadAllAsync()`:
   - If `SelectedEtfTicker` is null or "(All)", call `constituentService.IngestAllEtfsAsync(AsOfDate, _cts.Token)`
   - If specific ETF selected, call `constituentService.IngestEtfAsync(SelectedEtfTicker, AsOfDate, _cts.Token)`
   - Before starting: subscribe to service `ProgressUpdated` event, set `IsLoading = true`
   - After completion: unsubscribe from events, set `IsLoading = false`, log summary

2. `CancelCommand` → `Cancel()`:
   - Cancel via `_cts.Cancel()` — same pattern as existing `CancelBackfill()`
   - Log "Cancellation requested — finishing current ETF..."

3. `ClearLogCommand` → `ClearLog()`:
   - Same as existing — clears `LogMessages`

**Remove commands:** `LoadConstituentsCommand`, `StartBackfillCommand`, `TestConnectionCommand`

**Event handlers:**

Wire `constituentService.LogMessage` to the existing `Log()` helper (inserts at position 0, caps at 500, uses `Dispatcher.Invoke`).

Wire `constituentService.ProgressUpdated` to update:
- `CurrentEtfLabel` = `$"Loading {progress.EtfTicker} ({progress.CurrentEtf} / {progress.TotalEtfs})..."`
- `Progress` = `(double)progress.CurrentEtf / progress.TotalEtfs * 100`
- `ProgressText` = `$"{progress.Stats.Inserted} inserted, {progress.Stats.SkippedExisting} skipped, {progress.Stats.Failed} failed"`

**Month-end default date calculation:**
```csharp
private static DateTime GetLastMonthEnd()
{
    var today = DateTime.Today;
    var firstOfMonth = new DateTime(today.Year, today.Month, 1);
    var lastOfPrevMonth = firstOfMonth.AddDays(-1);
    // Walk back to last business day (skip weekends)
    while (lastOfPrevMonth.DayOfWeek is DayOfWeek.Saturday or DayOfWeek.Sunday)
        lastOfPrevMonth = lastOfPrevMonth.AddDays(-1);
    return lastOfPrevMonth;
}
```

**Verification:**
Run: `dotnet build projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
Expected: Build succeeds

**Commit:** `feat(eodhd-loader): rewrite IndexManagerViewModel for iShares constituent loading`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Tests for IndexManagerViewModel

**Verifies:** ishares-constituent-loader.AC4.1, ishares-constituent-loader.AC4.2, ishares-constituent-loader.AC4.3, ishares-constituent-loader.AC4.4, ishares-constituent-loader.AC4.5, ishares-constituent-loader.AC4.6

**Files:**
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/ViewModels/IndexManagerViewModelTests.cs`

**Testing:**

Use `Mock<IISharesConstituentService>` to control service behavior. Test the ViewModel's command logic and event wiring.

Tests must verify each AC listed above:

- **ishares-constituent-loader.AC4.1:** Call `LoadAllCommand` with no specific ETF selected. Assert `IngestAllEtfsAsync` was called on the mock service. Fire mock `ProgressUpdated` events and assert `CurrentEtfLabel`, `Progress`, `ProgressText` properties update correctly.
- **ishares-constituent-loader.AC4.2:** Set `SelectedEtfTicker` to "IVV". Call `LoadAllCommand`. Assert `IngestEtfAsync` was called with "IVV" (not `IngestAllEtfsAsync`).
- **ishares-constituent-loader.AC4.3:** Assert `AsOfDate` defaults to last business day of previous month. Change `AsOfDate` to a specific date, call `LoadAllCommand`, assert service was called with the changed date.
- **ishares-constituent-loader.AC4.4:** Fire mock `LogMessage` events during load. Assert messages appear in `LogMessages` collection in newest-first order.
- **ishares-constituent-loader.AC4.5:** Start a load, then call `CancelCommand`. Assert the CancellationToken passed to the service is cancelled.
- **ishares-constituent-loader.AC4.6:** Configure mock to throw on a specific ETF during `IngestAllEtfsAsync`. Assert the ViewModel does not crash — `IsLoading` returns to false, and the error is logged to `LogMessages`.

Note: WPF Dispatcher calls in `Log()` need to be handled in tests. Either mock the dispatcher or use `SynchronizationContext.SetSynchronizationContext(new SynchronizationContext())` in test setup to avoid cross-thread issues.

**Verification:**
Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/ --filter "FullyQualifiedName~IndexManagerViewModelTests"`
Expected: All tests pass

**Commit:** `test(eodhd-loader): add IndexManagerViewModel tests for AC4`
<!-- END_TASK_2 -->
<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 3-4) -->
## Subcomponent B: XAML View Update

<!-- START_TASK_3 -->
### Task 3: Rewrite IndexManagerView.xaml

**Files:**
- Modify: `projects/eodhd-loader/src/EodhdLoader/Views/IndexManagerView.xaml` (full rewrite)

**Implementation:**

Replace the XAML layout to match the new ViewModel properties. Keep the 6-row grid structure but change the controls.

**New layout:**

**Row 0: Header**
- "iShares Constituent Loader" title (replacing "Index Manager")
- No environment selector (removed — this service writes directly to local DB)

**Row 1: Configuration**
- GroupBox "Load Configuration"
- Row 0: "As-of Date" label + DatePicker bound to `AsOfDate`
- Row 1: "ETF" label + ComboBox bound to `SelectedEtfTicker` with items from `AvailableEtfTickers`. First item "(All)" = load all 277 ETFs.

**Row 2: Current Operation**
- GroupBox "Progress"
- `CurrentEtfLabel` TextBlock (e.g., "Loading IVV (3 / 277)...")
- ProgressBar bound to `Progress` (0-100)
- `ProgressText` TextBlock (e.g., "45 inserted, 3 skipped, 0 failed")

**Row 3: Actions**
- StackPanel, right-aligned
- "Clear Log" button → `ClearLogCommand`
- "Cancel" button → `CancelCommand` (enabled when `IsLoading`)
- "Load" button → `LoadAllCommand` (disabled when `IsLoading`, uses `InverseBoolConverter`)

**Row 4: Activity Log**
- GroupBox "Activity Log"
- ListBox bound to `LogMessages`, same Consolas 11pt monospace style as current
- Same `TextWrapping="NoWrap"` + horizontal scrollbar pattern

**Row 5:** Reserved for future use (empty or collapsed)

Remove references to: `InverseBoolConverter` for `IsLoadingConstituents` (removed), `EnvironmentConverter`, environment ComboBox, constituent count display, backfill date range pickers.

Keep: `InverseBoolConverter` (still used for `IsLoading` on Load button).

**Verification:**
Run: `dotnet build projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
Expected: Build succeeds, XAML parses without errors

**Commit:** `feat(eodhd-loader): rewrite IndexManagerView.xaml for iShares loading UI`
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Update MainWindow Tab Header

**Files:**
- Modify: `projects/eodhd-loader/src/EodhdLoader/MainWindow.xaml`

**Implementation:**

Update the tab header from `"Index Manager"` to `"iShares Loader"` to match the new functionality. Keep consistent with other tab names (Boris, Bulk Fill, Crawler, Dashboard) which do not use emoji prefixes. The tab is at index 3 in the TabControl (line ~31 of MainWindow.xaml):

```xml
<!-- Before -->
<TabItem Header="Index Manager">

<!-- After -->
<TabItem Header="iShares Loader">
```

No changes to DataContext binding (`{Binding IndexManager}` remains correct — the ViewModel property name stays the same in MainViewModel).

**Verification:**
Run: `dotnet build projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
Expected: Build succeeds

**Commit:** `chore(eodhd-loader): rename Index Manager tab to iShares Loader`
<!-- END_TASK_4 -->
<!-- END_SUBCOMPONENT_B -->

<!-- START_SUBCOMPONENT_C (tasks 5-6) -->
## Subcomponent C: DI Update and Cleanup

<!-- START_TASK_5 -->
### Task 5: Update DI Registration — Remove IndexService

**Files:**
- Modify: `projects/eodhd-loader/src/EodhdLoader/App.xaml.cs`
- Modify: `projects/eodhd-loader/src/EodhdLoader/ViewModels/MainViewModel.cs` (if IndexManagerViewModel constructor changed)

**Implementation:**

In `App.xaml.cs`:
1. Remove the `IndexService` registration: `services.AddHttpClient<IndexService>();` (line 31)
2. Verify `IISharesConstituentService` registration exists (added in Phase 1, Task 12): `services.AddHttpClient<IISharesConstituentService, ISharesConstituentService>();`
3. Update `IndexManagerViewModel` registration if constructor parameters changed. Since `IndexManagerViewModel` is registered as `AddTransient<IndexManagerViewModel>()` and uses constructor injection, the DI container will automatically resolve the new dependencies — just make sure the old `IndexService` and `StockAnalyzerApiClient` parameters are removed from the constructor.

In `MainViewModel.cs`:
- Check that `IndexManager` property still resolves correctly. The property type (`IndexManagerViewModel`) hasn't changed, just the constructor dependencies. DI handles this automatically.

Remove unused `using EodhdLoader.Services;` if `IndexService` was the only service from that namespace used in App.xaml.cs (it's not — other services like `BorisService`, `StockAnalyzerApiClient` are also used).

**Verification:**
Run: `dotnet build projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
Expected: Build succeeds with no unresolved dependency warnings

**Commit:** `refactor(eodhd-loader): remove IndexService from DI, wire ISharesConstituentService`
<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Delete IndexService and DTOs

**Files:**
- Delete: `projects/eodhd-loader/src/EodhdLoader/Services/IndexService.cs`

**Implementation:**

Delete the entire file. It contains:
- `IndexService` class (Wikipedia scraper)
- `IndexDefinition` DTO (not to be confused with `IndexDefinitionEntity`)
- `IndexConstituentsResponse` DTO
- `IndexConstituent` DTO (not to be confused with `IndexConstituentEntity`)
- Internal EODHD model stubs (`FundamentalsResponse`, `GeneralInfo`, `ComponentInfo`)

After deletion, verify no other files reference these types:
- Search for `IndexService` references across the project (should be none after Task 5 removed DI registration and Task 1 removed ViewModel dependency)
- Search for `IndexConstituentsResponse`, `IndexDefinition` (the DTO, not the entity) references
- If any remain, update them

**Verification:**
Run: `dotnet build projects/eodhd-loader/EodhdLoader.sln`
Expected: Both main project and test project build successfully with no missing reference errors

Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/`
Expected: All tests pass (Phase 1 + Phase 2 tests)

**Commit:** `refactor(eodhd-loader): remove Wikipedia-based IndexService and DTOs`
<!-- END_TASK_6 -->
<!-- END_SUBCOMPONENT_C -->
