# iShares Constituent Loader — Phase 1: Core Service

**Goal:** Port the Python iShares ingestion pipeline to C# as `ISharesConstituentService` with full EF Core entity mapping, unit tests with mocking, and enterprise-grade test coverage.

**Architecture:** Single service class in the EODHD Loader downloads iShares ETF holdings JSON, auto-detects Format A/B column layouts, parses equity holdings, matches/creates securities via 3-level lookup, upserts identifiers with SCD Type 2 history, and inserts constituent records idempotently via EF Core. Test project uses xUnit + Moq + EF Core InMemory provider.

**Tech Stack:** C# / .NET 9, EF Core (SQL Server + InMemory for tests), xUnit, Moq, System.Text.Json, HttpClient via IHttpClientFactory

**Scope:** 4 phases from original design (this is phase 1 of 4)

**Codebase verified:** 2026-02-22

**Critical design plan discrepancy:** The design states "All target entities exist" and "No schema changes needed." This is incorrect. `IndexDefinitionEntity`, `IndexConstituentEntity`, `SecurityIdentifierEntity`, and `SecurityIdentifierHistEntity` do NOT exist as EF Core entities. The Python pipeline wrote to these tables via raw SQL. This phase creates the entities and a baseline migration.

---

## Acceptance Criteria Coverage

This phase implements and tests:

### ishares-constituent-loader.AC1: JSON Download
- **ishares-constituent-loader.AC1.1 Success:** Service downloads holdings JSON for a valid ETF ticker and as-of date
- **ishares-constituent-loader.AC1.2 Success:** BOM-prefixed responses are handled without parse errors
- **ishares-constituent-loader.AC1.3 Failure:** Unknown ETF ticker returns null/empty result (no exception)
- **ishares-constituent-loader.AC1.4 Failure:** Network timeout after 60s returns null/empty result with logged error
- **ishares-constituent-loader.AC1.5 Edge:** Weekend as-of date is adjusted to last business day (Friday)

### ishares-constituent-loader.AC2: Holdings Parsing
- **ishares-constituent-loader.AC2.1 Success:** Format A JSON (IVV-style, 17 cols) parses all equity holdings with correct weights
- **ishares-constituent-loader.AC2.2 Success:** Format B JSON (IJK-style, 19 cols) parses all equity holdings with correct weights
- **ishares-constituent-loader.AC2.3 Success:** Non-equity rows (Cash, Futures, Money Market) are filtered out
- **ishares-constituent-loader.AC2.4 Failure:** Malformed JSON returns empty holdings list (no exception)
- **ishares-constituent-loader.AC2.5 Edge:** Holdings with missing weight or market value are included with null values

### ishares-constituent-loader.AC3: Database Persistence
- **ishares-constituent-loader.AC3.1 Success:** New securities are created in SecurityMaster with correct fields
- **ishares-constituent-loader.AC3.2 Success:** Existing securities are matched by ticker, then CUSIP, then ISIN (3-level lookup)
- **ishares-constituent-loader.AC3.3 Success:** SecurityIdentifier rows are upserted; changed values trigger SCD Type 2 history snapshot
- **ishares-constituent-loader.AC3.4 Success:** IndexConstituent records are inserted with correct Weight, MarketValue, Shares, Sector, SourceId
- **ishares-constituent-loader.AC3.5 Success:** Duplicate constituent inserts (same IndexId + SecurityAlias + EffectiveDate + SourceId) are skipped idempotently
- **ishares-constituent-loader.AC3.6 Failure:** DB write failure for one holding does not abort the entire ETF — remaining holdings are processed

---

## Reference Files

The executor should read these files for context:

- **Python pipeline (port source):** `c:/Users/patri/Documents/claudeProjects/helpers/ishares_ingest.py`
- **ETF config:** `c:/Users/patri/Documents/claudeProjects/helpers/ishares_etf_configs.json`
- **Seed SQL (table schemas):** `c:/Users/patri/Documents/claudeProjects/projects/stock-analyzer/src/StockAnalyzer.Core/scripts/seed_index_attribution.sql`
- **SecurityMasterEntity (pattern):** `c:/Users/patri/Documents/claudeProjects/projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityMasterEntity.cs`
- **SourceEntity (pattern):** `c:/Users/patri/Documents/claudeProjects/projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SourceEntity.cs`
- **StockAnalyzerDbContext:** `c:/Users/patri/Documents/claudeProjects/projects/stock-analyzer/src/StockAnalyzer.Core/Data/StockAnalyzerDbContext.cs`
- **App.xaml.cs (DI):** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/App.xaml.cs`
- **EodhdLoader.csproj:** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
- **Solution file:** `c:/Users/patri/Documents/claudeProjects/projects/eodhd-loader/EodhdLoader.sln`

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->
## Subcomponent A: EF Core Entities + Migration

<!-- START_TASK_1 -->
### Task 1: Create EF Core Entity Classes for Index Attribution Tables

**Files:**
- Create: `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/IndexDefinitionEntity.cs`
- Create: `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/IndexConstituentEntity.cs`
- Create: `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityIdentifierEntity.cs`
- Create: `projects/stock-analyzer/src/StockAnalyzer.Core/Data/Entities/SecurityIdentifierHistEntity.cs`

**Implementation:**

Create four entity classes matching the existing database tables (created by Python pipeline via raw SQL). Follow the existing pattern from `SecurityMasterEntity.cs` — file-scoped namespace, XML doc comments, proper nullable annotations.

**IndexDefinitionEntity** — maps `[data].IndexDefinition`:
- `IndexId` (int, PK, identity) — auto-increment
- `IndexCode` (string, required, max 20) — e.g., "SP500", "R1000"
- `IndexName` (string, required, max 200) — e.g., "S&P 500"
- `IndexFamily` (string, nullable, max 50) — e.g., "S&P", "Russell", "MSCI"
- `WeightingMethod` (string, nullable, max 50) — e.g., "FloatAdjustedMarketCap"
- `Region` (string, nullable, max 100) — e.g., "US", "Emerging Markets"
- `ProxyEtfTicker` (string, nullable, max 20) — e.g., "IVV", "IWB"
- Navigation: `ICollection<IndexConstituentEntity> Constituents`

**IndexConstituentEntity** — maps `[data].IndexConstituent`:
- `Id` (int, PK, identity) — auto-increment surrogate key
- `IndexId` (int, FK to IndexDefinition) — required
- `SecurityAlias` (int, FK to SecurityMaster) — required
- `EffectiveDate` (DateTime, date-only) — snapshot date
- `Weight` (decimal?, precision 18,8) — weight as decimal (0.065432 = 6.5432%)
- `MarketValue` (decimal?, precision 18,2) — market value in USD
- `Shares` (decimal?, precision 18,4) — number of shares held
- `Sector` (string, nullable, max 100) — GICS sector
- `Location` (string, nullable, max 100) — domicile country
- `Currency` (string, nullable, max 10) — trading currency
- `SourceId` (int, FK to Sources) — data source (10 = iShares)
- `SourceTicker` (string, nullable, max 20) — ticker as reported by source
- Navigation: `IndexDefinitionEntity IndexDefinition`, `SecurityMasterEntity Security`, `SourceEntity Source`

**SecurityIdentifierEntity** — maps `[data].SecurityIdentifier`:
- `SecurityAlias` (int, composite PK part 1, FK to SecurityMaster)
- `IdentifierType` (string, composite PK part 2, max 20) — "CUSIP", "ISIN", "SEDOL"
- `IdentifierValue` (string, required, max 50) — the identifier value
- `SourceId` (int, FK to Sources) — who provided this identifier
- `UpdatedBy` (string, nullable, max 100) — e.g., "ishares-ingest"
- `UpdatedAt` (DateTime) — last update timestamp
- Navigation: `SecurityMasterEntity Security`

**SecurityIdentifierHistEntity** — maps `[data].SecurityIdentifierHist`:
- `Id` (int, PK, identity) — auto-increment
- `SecurityAlias` (int, FK to SecurityMaster)
- `IdentifierType` (string, required, max 20)
- `IdentifierValue` (string, required, max 50)
- `EffectiveFrom` (DateTime, date-only) — when this value became active
- `EffectiveTo` (DateTime, date-only) — when this value was superseded
- `SourceId` (int, FK to Sources)

**Known tech debt:** The existing `SourceEntity.cs` is missing `SourceType` and `UpdatedBy` columns that exist in the database `Sources` table (used in `seed_index_attribution.sql`). EF Core does not require all columns to be mapped, so this works. Do NOT add these columns as part of this feature — it would require a separate migration and is out of scope.

**Verification:**
Run: `dotnet build projects/stock-analyzer/src/StockAnalyzer.Core/StockAnalyzer.Core.csproj`
Expected: Build succeeds

**Commit:** `feat(core): add EF Core entities for IndexDefinition, IndexConstituent, SecurityIdentifier, SecurityIdentifierHist`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Register Entities in StockAnalyzerDbContext

**Files:**
- Modify: `projects/stock-analyzer/src/StockAnalyzer.Core/Data/StockAnalyzerDbContext.cs`

**Implementation:**

Add DbSet properties and Fluent API configuration for the four new entities. Place them in the "Domain data tables (data schema)" section, after `CompanyBios`.

**DbSet declarations** (add after line 31, in the domain data section):
```csharp
public DbSet<IndexDefinitionEntity> IndexDefinitions => Set<IndexDefinitionEntity>();
public DbSet<IndexConstituentEntity> IndexConstituents => Set<IndexConstituentEntity>();
public DbSet<SecurityIdentifierEntity> SecurityIdentifiers => Set<SecurityIdentifierEntity>();
public DbSet<SecurityIdentifierHistEntity> SecurityIdentifierHistory => Set<SecurityIdentifierHistEntity>();
```

**Fluent API configuration** (add in `OnModelCreating`, after CompanyBio configuration):

IndexDefinitionEntity:
- `ToTable("IndexDefinition", "data")`
- PK on `IndexId` with `UseIdentityColumn()`
- `IndexCode` max 20, required, unique index `IX_IndexDefinition_IndexCode`
- `IndexName` max 200, required
- `IndexFamily` max 50, `WeightingMethod` max 50, `Region` max 100, `ProxyEtfTicker` max 20
- One-to-many relationship with `IndexConstituentEntity`

IndexConstituentEntity:
- `ToTable("IndexConstituent", "data")`
- PK on `Id` with `UseIdentityColumn()`
- `EffectiveDate` column type "date"
- `Weight` precision 18,8; `MarketValue` precision 18,2; `Shares` precision 18,4
- `Sector` max 100, `Location` max 100, `Currency` max 10, `SourceTicker` max 20
- Unique composite index on `(IndexId, SecurityAlias, EffectiveDate, SourceId)` named `IX_IndexConstituent_Unique`
- Index on `(IndexId, EffectiveDate)` named `IX_IndexConstituent_IndexDate`
- FK to IndexDefinition, SecurityMaster, Source (no cascade delete — data integrity)

SecurityIdentifierEntity:
- `ToTable("SecurityIdentifier", "data")`
- Composite PK on `(SecurityAlias, IdentifierType)`
- `IdentifierType` max 20, `IdentifierValue` max 50 required
- `UpdatedBy` max 100
- `UpdatedAt` default `GETUTCDATE()`
- Index on `(IdentifierType, IdentifierValue)` named `IX_SecurityIdentifier_TypeValue` for reverse lookup
- FK to SecurityMaster (no cascade delete)

SecurityIdentifierHistEntity:
- `ToTable("SecurityIdentifierHist", "data")`
- PK on `Id` with `UseIdentityColumn()`
- `IdentifierType` max 20 required, `IdentifierValue` max 50 required
- `EffectiveFrom` and `EffectiveTo` column type "date"
- Index on `(SecurityAlias, IdentifierType)` named `IX_SecurityIdentifierHist_AliasType`
- FK to SecurityMaster (no cascade delete)

**Verification:**
Run: `dotnet build projects/stock-analyzer/src/StockAnalyzer.Core/StockAnalyzer.Core.csproj`
Expected: Build succeeds

**Commit:** `feat(core): register index attribution entities in StockAnalyzerDbContext`
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Create Baseline EF Core Migration

**Files:**
- Create: `projects/stock-analyzer/src/StockAnalyzer.Core/Migrations/YYYYMMDD_MapIndexAttributionTables.cs` (auto-generated)

**Implementation:**

These tables already exist in the database (created by the Python pipeline). The migration must be a "baseline" — it registers in `__EFMigrationsHistory` without trying to create tables that already exist.

**Step 1: Generate the migration**
```powershell
cd projects/stock-analyzer/src/StockAnalyzer.Api
dotnet ef migrations add MapIndexAttributionTables --project ../StockAnalyzer.Core/StockAnalyzer.Core.csproj --startup-project .
```

**Step 2: Empty the generated migration**

Open the generated migration file. Replace the contents of `Up(MigrationBuilder migrationBuilder)` and `Down(MigrationBuilder migrationBuilder)` with empty bodies (remove all `CreateTable`, `CreateIndex`, `DropTable` calls). Keep the class structure and `BuildTargetModel` snapshot intact. Add a comment explaining why:

```csharp
protected override void Up(MigrationBuilder migrationBuilder)
{
    // Baseline migration: IndexDefinition, IndexConstituent, SecurityIdentifier,
    // and SecurityIdentifierHist tables already exist (created by Python pipeline).
    // This migration registers EF Core entity mappings without altering the schema.
}

protected override void Down(MigrationBuilder migrationBuilder)
{
    // No-op: these tables are managed externally and should not be dropped.
}
```

**Step 3: Apply migration to register it**
```powershell
# Ensure SQL Express is running
net start MSSQL$SQLEXPRESS

cd projects/stock-analyzer/src/StockAnalyzer.Api
dotnet ef database update --project ../StockAnalyzer.Core/StockAnalyzer.Core.csproj --startup-project . --connection "Server=.\SQLEXPRESS;Database=StockAnalyzer;Trusted_Connection=True;TrustServerCertificate=True"
```

**Verification:**
Run: Migration applies without errors
Run: `dotnet build projects/stock-analyzer/src/StockAnalyzer.Core/StockAnalyzer.Core.csproj`
Expected: Build succeeds, migration registered in `__EFMigrationsHistory`

**Commit:** `feat(core): add baseline migration for index attribution tables`
<!-- END_TASK_3 -->
<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 4-5) -->
## Subcomponent B: Test Project + Models + Config

<!-- START_TASK_4 -->
### Task 4: Create Test Project with xUnit + Moq

**Files:**
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/EodhdLoader.Tests.csproj`
- Modify: `projects/eodhd-loader/EodhdLoader.sln`

**Implementation:**

Create a standard xUnit test project that references the main EodhdLoader project.

**Step 1: Create the test project**
```powershell
cd projects/eodhd-loader
dotnet new xunit -o tests/EodhdLoader.Tests --framework net8.0-windows10.0.19041
```

**Step 2: Add project references and packages**
```powershell
cd projects/eodhd-loader/tests/EodhdLoader.Tests
dotnet add reference ../../src/EodhdLoader/EodhdLoader.csproj
dotnet add package Moq
dotnet add package Microsoft.EntityFrameworkCore.InMemory
```

**Step 3: Add to solution**
```powershell
cd projects/eodhd-loader
dotnet sln add tests/EodhdLoader.Tests/EodhdLoader.Tests.csproj
```

**Step 4: Verify build**
```powershell
dotnet build projects/eodhd-loader/EodhdLoader.sln
```

**Verification:**
Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/EodhdLoader.Tests.csproj`
Expected: Default placeholder test passes (or 0 tests if no placeholder generated)

**Commit:** `chore(eodhd-loader): add xUnit test project with Moq and EF Core InMemory`
<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Create Models and Bundle ETF Config

**Files:**
- Create: `projects/eodhd-loader/src/EodhdLoader/Models/ISharesHolding.cs`
- Create: `projects/eodhd-loader/src/EodhdLoader/Models/IngestProgress.cs`
- Create: `projects/eodhd-loader/src/EodhdLoader/Models/EtfConfig.cs`
- Copy: `helpers/ishares_etf_configs.json` -> `projects/eodhd-loader/src/EodhdLoader/Resources/ishares_etf_configs.json`
- Modify: `projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`

**Implementation:**

**ISharesHolding** — parsed holding DTO (mirrors Python `holding` dict):
```csharp
namespace EodhdLoader.Models;

public record ISharesHolding(
    string Ticker,
    string Name,
    string? Sector,
    decimal? MarketValue,
    decimal? Weight,        // Decimal fraction (0.065 = 6.5%)
    decimal? Shares,
    string? Location,
    string? Exchange,
    string? Currency,
    string? Cusip,
    string? Isin,
    string? Sedol
);
```

**IngestProgress** — progress reporting DTO:
```csharp
namespace EodhdLoader.Models;

public record IngestProgress(
    string EtfTicker,
    int CurrentEtf,
    int TotalEtfs,
    int HoldingsProcessed,
    int TotalHoldings,
    IngestStats Stats
);

public record IngestStats(
    int Parsed,
    int Matched,
    int Created,
    int Inserted,
    int SkippedExisting,
    int Failed,
    int IdentifiersSet
);
```

**EtfConfig** — ETF configuration from ishares_etf_configs.json:
```csharp
namespace EodhdLoader.Models;

public class EtfConfig
{
    public int ProductId { get; set; }
    public string Slug { get; set; } = string.Empty;
    public string IndexCode { get; set; } = string.Empty;
}
```

**Bundle the config file:** Copy `helpers/ishares_etf_configs.json` to `projects/eodhd-loader/src/EodhdLoader/Resources/`. Add to `.csproj`:
```xml
<ItemGroup>
  <Content Include="Resources\ishares_etf_configs.json">
    <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
  </Content>
</ItemGroup>
```

**Verification:**
Run: `dotnet build projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
Expected: Build succeeds, `ishares_etf_configs.json` copied to output directory

**Commit:** `feat(eodhd-loader): add iShares models and bundle ETF config`
<!-- END_TASK_5 -->
<!-- END_SUBCOMPONENT_B -->

<!-- START_SUBCOMPONENT_C (tasks 6-7) -->
## Subcomponent C: JSON Download (AC1)

<!-- START_TASK_6 -->
### Task 6: IISharesConstituentService Interface + JSON Download

**Verifies:** ishares-constituent-loader.AC1.1, ishares-constituent-loader.AC1.2, ishares-constituent-loader.AC1.3, ishares-constituent-loader.AC1.4, ishares-constituent-loader.AC1.5

**Files:**
- Create: `projects/eodhd-loader/src/EodhdLoader/Services/IISharesConstituentService.cs`
- Create: `projects/eodhd-loader/src/EodhdLoader/Services/ISharesConstituentService.cs`

**Implementation:**

**Interface** — defines the public contract:
```csharp
namespace EodhdLoader.Services;

using EodhdLoader.Models;

public interface IISharesConstituentService
{
    /// <summary>Downloads and parses holdings for a single ETF, persists to database.</summary>
    Task<IngestStats> IngestEtfAsync(string etfTicker, DateTime? asOfDate = null, CancellationToken ct = default);

    /// <summary>Loads all configured ETFs with rate limiting.</summary>
    Task IngestAllEtfsAsync(DateTime? asOfDate = null, CancellationToken ct = default);

    /// <summary>Returns ETFs with stale constituent data (missing latest month-end).</summary>
    Task<IReadOnlyList<(string EtfTicker, string IndexCode)>> GetStaleEtfsAsync(CancellationToken ct = default);

    /// <summary>All configured ETF tickers.</summary>
    IReadOnlyDictionary<string, EtfConfig> EtfConfigs { get; }

    /// <summary>Raised for each log-worthy event during ingestion.</summary>
    event Action<string>? LogMessage;

    /// <summary>Raised for progress tracking during bulk operations.</summary>
    event Action<IngestProgress>? ProgressUpdated;
}
```

**Service class** — implement constructor, config loading, and download methods first. Other methods will be added in later tasks.

Constructor takes `IHttpClientFactory` and `StockAnalyzerDbContext` via DI. Loads ETF configs from bundled JSON at startup.

Key implementation details for download:

1. **URL construction** — port from Python `download_holdings_json()` (ishares_ingest.py:116-142):
   ```
   https://www.ishares.com/us/products/{product_id}/{slug}/1467271812596.ajax?fileType=json&tab=all&asOfDate={YYYYMMDD}
   ```

2. **BOM handling** — strip UTF-8 BOM (`\uFEFF`) before JSON parsing (mirrors Python line 138):
   ```csharp
   var text = await response.Content.ReadAsStringAsync(ct);
   text = text.TrimStart('\uFEFF');
   ```

3. **Timeout** — 60-second timeout on HttpClient (AC1.4)

4. **User-Agent** — `"StockAnalyzer/1.0 (academic-research; single-concurrency; 2s-gap)"` (mirrors Python line 69)

5. **Weekend date adjustment** — port `find_last_business_day()` (ishares_ingest.py:392-397):
   ```csharp
   private static DateTime AdjustToLastBusinessDay(DateTime date)
   {
       while (date.DayOfWeek is DayOfWeek.Saturday or DayOfWeek.Sunday)
           date = date.AddDays(-1);
       return date;
   }
   ```

6. **Error handling** — catch `HttpRequestException`, `TaskCanceledException`, `JsonException`. Return null on failure, log the error. Never throw.

7. **Rate limiting constant** — `public const int RequestDelayMs = 2000;` (public so CrawlerViewModel can reference it instead of hardcoding its own 2s delay)

8. **iShares Source ID constant** — `private const int ISharesSourceId = 10;`

**Verification:**
Run: `dotnet build projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
Expected: Build succeeds

**Commit:** `feat(eodhd-loader): add IISharesConstituentService interface and download implementation`
<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: Tests for JSON Download (AC1)

**Verifies:** ishares-constituent-loader.AC1.1, ishares-constituent-loader.AC1.2, ishares-constituent-loader.AC1.3, ishares-constituent-loader.AC1.4, ishares-constituent-loader.AC1.5

**Files:**
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceDownloadTests.cs`

**Testing:**

Use `Mock<HttpMessageHandler>` to control HTTP responses. Create a helper method that builds an `ISharesConstituentService` with a mocked HTTP client and an EF Core InMemory `StockAnalyzerDbContext`.

Tests must verify each AC listed above:

- **ishares-constituent-loader.AC1.1:** Mock returns 200 with valid iShares JSON body. Assert returned data is not null and contains expected `aaData` structure.
- **ishares-constituent-loader.AC1.2:** Mock returns 200 with `\uFEFF` prefix prepended to valid JSON. Assert parsing succeeds without error.
- **ishares-constituent-loader.AC1.3:** Call with an ETF ticker not in `ishares_etf_configs.json` (e.g., "ZZZZZ"). Assert returns null/empty, no exception thrown.
- **ishares-constituent-loader.AC1.4:** Mock throws `TaskCanceledException` (simulating timeout). Assert returns null/empty, no exception propagated.
- **ishares-constituent-loader.AC1.5:** Call with a Saturday date (e.g., `2025-01-25`). Assert the HTTP request URL contains `asOfDate=20250124` (Friday).

**Verification:**
Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/ --filter "FullyQualifiedName~DownloadTests"`
Expected: All tests pass

**Commit:** `test(eodhd-loader): add download tests for AC1 (JSON download, BOM, errors, date adjustment)`
<!-- END_TASK_7 -->
<!-- END_SUBCOMPONENT_C -->

<!-- START_SUBCOMPONENT_D (tasks 8-9) -->
## Subcomponent D: Holdings Parsing (AC2)

<!-- START_TASK_8 -->
### Task 8: Holdings Parsing Implementation

**Verifies:** ishares-constituent-loader.AC2.1, ishares-constituent-loader.AC2.2, ishares-constituent-loader.AC2.3, ishares-constituent-loader.AC2.4, ishares-constituent-loader.AC2.5

**Files:**
- Modify: `projects/eodhd-loader/src/EodhdLoader/Services/ISharesConstituentService.cs`

**Implementation:**

Add holdings parsing methods to the service. Port from Python `parse_holdings()` (ishares_ingest.py:197-243) and `_detect_format()` (ishares_ingest.py:170-181).

Key implementation details:

1. **Format detection** — iShares JSON has `aaData` array of arrays. Each inner array is one holding row.
   - Format A (IVV-style, 17 cols): `row[4]` is a JsonElement with `ValueKind == Object` (dict `{display, raw}`)
   - Format B (IJK-style, 19 cols): `row[4]` is a string `"Equity"`
   - Detection: `if (firstRow.Count >= 19 && firstRow[4].ValueKind == JsonValueKind.String)` → Format B, else Format A

2. **Column indices** — port from Python `COL_A` and `COL_B` (ishares_ingest.py:97-109):
   - Format A: ticker=0, name=1, sector=2, assetClass=3, marketValue=4, weight=5, quantity=7
   - Format B: ticker=0, name=1, sector=3, assetClass=4, marketValue=5, weight=17, quantity=7
   - Common: cusip=8, isin=9, sedol=10, price=11, location=12, exchange=13, currency=14

3. **Non-equity filtering** — skip rows where asset class is in: `{"Cash", "Cash Collateral and Margins", "Cash and/or Derivatives", "Futures", "Money Market"}` (mirrors Python line 191-194)

4. **Value extraction** — port `_raw_float()` (ishares_ingest.py:152-167):
   - If cell is a JSON object with `raw` property → extract numeric value
   - If cell is a string → strip commas, handle "-", "", "N/A" as null
   - Weight is percentage in source (e.g., 6.5) → divide by 100 to get decimal (0.065)

5. **Identifier cleaning** — port `_clean_id()` (ishares_ingest.py:184-188): strip whitespace, return null for "-", "", "N/A"

6. **Return type** — `List<ISharesHolding>` (using the record from Task 5)

Make the parsing method `internal` so it's testable from the test project (add `[InternalsVisibleTo("EodhdLoader.Tests")]` to the main project's AssemblyInfo or csproj).

**Verification:**
Run: `dotnet build projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
Expected: Build succeeds

**Commit:** `feat(eodhd-loader): implement iShares holdings parsing with Format A/B auto-detection`
<!-- END_TASK_8 -->

<!-- START_TASK_9 -->
### Task 9: Tests for Holdings Parsing (AC2)

**Verifies:** ishares-constituent-loader.AC2.1, ishares-constituent-loader.AC2.2, ishares-constituent-loader.AC2.3, ishares-constituent-loader.AC2.4, ishares-constituent-loader.AC2.5

**Files:**
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServiceParsingTests.cs`
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/TestData/format_a_sample.json`
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/TestData/format_b_sample.json`

**Testing:**

Create minimal but representative JSON test fixtures for Format A and Format B. Each should include:
- 2-3 equity holdings with all fields populated
- 1 Cash/Futures row (to verify filtering)
- 1 holding with missing weight/market value (to verify null handling)

Tests must verify each AC listed above:

- **ishares-constituent-loader.AC2.1:** Parse Format A sample JSON. Assert correct number of equity holdings returned. Assert first holding has correct ticker, name, sector, weight (divided by 100), market value, shares, CUSIP, ISIN.
- **ishares-constituent-loader.AC2.2:** Parse Format B sample JSON. Assert correct number of equity holdings returned. Assert weight comes from column index 17 (not 5). Assert sector comes from column index 3 (not 2).
- **ishares-constituent-loader.AC2.3:** Both samples include non-equity rows (Cash, Futures). Assert those rows are NOT in the returned holdings list. Assert count matches only equity rows.
- **ishares-constituent-loader.AC2.4:** Pass malformed JSON string (e.g., `"not json"` or `"{}"` with no aaData). Assert returns empty list, no exception thrown.
- **ishares-constituent-loader.AC2.5:** Include a holding with `"-"` for weight and `"N/A"` for market value. Assert the returned holding has `Weight == null` and `MarketValue == null` but is still included in the list.

**Verification:**
Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/ --filter "FullyQualifiedName~ParsingTests"`
Expected: All tests pass

**Commit:** `test(eodhd-loader): add parsing tests for AC2 (Format A, Format B, filtering, edge cases)`
<!-- END_TASK_9 -->
<!-- END_SUBCOMPONENT_D -->

<!-- START_SUBCOMPONENT_E (tasks 10-11) -->
## Subcomponent E: Database Persistence (AC3)

<!-- START_TASK_10 -->
### Task 10: Database Persistence Implementation

**Verifies:** ishares-constituent-loader.AC3.1, ishares-constituent-loader.AC3.2, ishares-constituent-loader.AC3.3, ishares-constituent-loader.AC3.4, ishares-constituent-loader.AC3.5, ishares-constituent-loader.AC3.6

**Files:**
- Modify: `projects/eodhd-loader/src/EodhdLoader/Services/ISharesConstituentService.cs`

**Implementation:**

Complete the `IngestEtfAsync` method. Port from Python `ingest_etf()` (ishares_ingest.py:400-516).

Key implementation details:

1. **Orchestration flow** (mirrors Python lines 400-516):
   - Look up `EtfConfig` by ticker → return empty stats if not found
   - Adjust date to last business day if weekend
   - Download JSON → return empty stats if null
   - Parse holdings → return stats with parsed count if empty
   - Look up `IndexId` from `IndexDefinition` by `IndexCode`
   - For each holding: match/create security → upsert identifiers → check existing → insert constituent
   - Track stats: parsed, matched, created, inserted, skippedExisting, failed, identifiersSet

2. **3-level security matching** (port from Python lines 460-466):
   ```csharp
   // Level 1: Ticker lookup
   var security = await _dbContext.SecurityMaster
       .FirstOrDefaultAsync(s => s.TickerSymbol == holding.Ticker, ct);

   // Level 2: CUSIP lookup
   if (security == null && holding.Cusip != null)
   {
       var identifier = await _dbContext.SecurityIdentifiers
           .FirstOrDefaultAsync(si => si.IdentifierType == "CUSIP" && si.IdentifierValue == holding.Cusip, ct);
       if (identifier != null)
           security = await _dbContext.SecurityMaster.FindAsync(new object[] { identifier.SecurityAlias }, ct);
   }

   // Level 3: ISIN lookup
   if (security == null && holding.Isin != null)
   {
       var identifier = await _dbContext.SecurityIdentifiers
           .FirstOrDefaultAsync(si => si.IdentifierType == "ISIN" && si.IdentifierValue == holding.Isin, ct);
       if (identifier != null)
           security = await _dbContext.SecurityMaster.FindAsync(new object[] { identifier.SecurityAlias }, ct);
   }
   ```

3. **Security creation** (port from Python `create_security()` lines 286-307):
   - Create `SecurityMasterEntity` with: PrimaryAssetId (CUSIP or ISIN), IssueName, TickerSymbol, Exchange, SecurityType="Common Stock", Country (from Location), Currency, Isin, IsActive=true, timestamps
   - Add to context, SaveChanges to get generated SecurityAlias

4. **Identifier upsert with SCD Type 2** (port from Python `upsert_security_identifier()` lines 310-354):
   - For each identifier type (CUSIP, ISIN, SEDOL):
     - If value is null/empty → skip
     - Query existing `SecurityIdentifier` by (SecurityAlias, IdentifierType)
     - If exists and value unchanged → skip
     - If exists and value CHANGED → snapshot old to `SecurityIdentifierHist` (EffectiveFrom=existing.UpdatedAt, EffectiveTo=today), then update current
     - If not exists → insert new
   - SaveChanges after all three identifiers processed

5. **Idempotent constituent insert** (port from Python `check_existing_constituent()` + `insert_constituent()` lines 357-385):
   - Check if `IndexConstituent` exists with same (IndexId, SecurityAlias, EffectiveDate, SourceId)
   - If exists → skip (increment skippedExisting)
   - If not → insert with all fields, SaveChanges

6. **Error isolation per holding** (AC3.6):
   - Wrap each holding's processing in try/catch
   - On failure: log warning, increment failed count, continue to next holding
   - Use separate SaveChanges per holding to prevent one failure from rolling back others

7. **`IngestAllEtfsAsync` implementation** — bulk loading loop with rate limiting:
   ```csharp
   public async Task IngestAllEtfsAsync(DateTime? asOfDate = null, CancellationToken ct = default)
   {
       var etfTickers = EtfConfigs.Keys.ToList();
       int current = 0;

       foreach (var ticker in etfTickers)
       {
           ct.ThrowIfCancellationRequested();
           current++;

           try
           {
               var stats = await IngestEtfAsync(ticker, asOfDate, ct);
               ProgressUpdated?.Invoke(new IngestProgress(ticker, current, etfTickers.Count, 0, 0, stats));
               LogMessage?.Invoke($"{ticker}: {stats.Inserted} inserted, {stats.SkippedExisting} skipped, {stats.Failed} failed");
           }
           catch (Exception ex) when (ex is not OperationCanceledException)
           {
               LogMessage?.Invoke($"{ticker}: FAILED — {ex.Message}");
               ProgressUpdated?.Invoke(new IngestProgress(ticker, current, etfTickers.Count, 0, 0,
                   new IngestStats(0, 0, 0, 0, 0, 1, 0)));
           }

           // Rate limiting — minimum 2s between iShares requests
           if (current < etfTickers.Count)
               await Task.Delay(RequestDelayMs, ct);
       }
   }
   ```
   This method is called by `IndexManagerViewModel.LoadAllAsync()` (Phase 2). The `RequestDelayMs` constant (2000) enforces AC6.1. The `ProgressUpdated` event drives the UI progress bar. Individual ETF failures are caught and logged without aborting the batch.

**Verification:**
Run: `dotnet build projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj`
Expected: Build succeeds

**Commit:** `feat(eodhd-loader): implement database persistence with 3-level matching, SCD Type 2, idempotent inserts`
<!-- END_TASK_10 -->

<!-- START_TASK_11 -->
### Task 11: Tests for Database Persistence (AC3)

**Verifies:** ishares-constituent-loader.AC3.1, ishares-constituent-loader.AC3.2, ishares-constituent-loader.AC3.3, ishares-constituent-loader.AC3.4, ishares-constituent-loader.AC3.5, ishares-constituent-loader.AC3.6

**Files:**
- Create: `projects/eodhd-loader/tests/EodhdLoader.Tests/Services/ISharesConstituentServicePersistenceTests.cs`

**Testing:**

Use EF Core InMemory provider to create a test `StockAnalyzerDbContext`. Pre-seed with:
- An `IndexDefinitionEntity` (IndexCode="SP500", ProxyEtfTicker="IVV")
- A `SourceEntity` (SourceId=10, SourceShortName="iShares")
- Optionally, a few `SecurityMasterEntity` entries for matching tests

Mock `HttpMessageHandler` to return pre-built Format A JSON with known holdings.

Tests must verify each AC listed above:

- **ishares-constituent-loader.AC3.1:** Ingest an ETF where holdings have tickers not in SecurityMaster. Assert new `SecurityMasterEntity` rows created with correct IssueName, TickerSymbol, Exchange, SecurityType, Country, Currency, Isin, IsActive.
- **ishares-constituent-loader.AC3.2:** Pre-seed SecurityMaster with a security by ticker. Pre-seed SecurityIdentifier with a CUSIP entry for a different security. Pre-seed SecurityIdentifier with an ISIN entry for a third security. Ingest holdings that match each level. Assert each holding matched the correct SecurityAlias (level 1 by ticker, level 2 by CUSIP, level 3 by ISIN).
- **ishares-constituent-loader.AC3.3:** Pre-seed SecurityIdentifier with SecurityAlias=1, IdentifierType="CUSIP", IdentifierValue="OLD_CUSIP". Ingest a holding for SecurityAlias=1 with a DIFFERENT CUSIP. Assert SecurityIdentifierHist row created with old value and date range. Assert SecurityIdentifier row updated to new value.
- **ishares-constituent-loader.AC3.4:** Ingest a holding with known Weight, MarketValue, Shares, Sector. Query IndexConstituent after ingestion. Assert all fields match expected values, SourceId=10, SourceTicker matches holding ticker.
- **ishares-constituent-loader.AC3.5:** Ingest the same ETF + date twice. Assert IndexConstituent count after second run equals count after first run (no duplicates). Assert stats show skippedExisting > 0 on second run. **Note:** EF Core InMemory provider does not enforce unique constraints, so this test validates the application-level duplicate check (the `AnyAsync` guard before insert), not the database-level `IX_IndexConstituent_Unique` composite index. The database constraint serves as a safety net in production but cannot be verified in InMemory tests.
- **ishares-constituent-loader.AC3.6:** Create a scenario where one holding causes a SaveChanges failure (e.g., by pre-seeding conflicting data or using a mock that throws on specific input). Assert the service continues processing remaining holdings. Assert stats.Failed > 0 and stats.Inserted > 0 (other holdings succeeded).

**Verification:**
Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/ --filter "FullyQualifiedName~PersistenceTests"`
Expected: All tests pass

**Commit:** `test(eodhd-loader): add persistence tests for AC3 (matching, SCD Type 2, idempotent, error isolation)`
<!-- END_TASK_11 -->
<!-- END_SUBCOMPONENT_E -->

<!-- START_TASK_12 -->
### Task 12: DI Registration and Service Wiring

**Files:**
- Modify: `projects/eodhd-loader/src/EodhdLoader/App.xaml.cs`
- Modify: `projects/eodhd-loader/src/EodhdLoader/EodhdLoader.csproj` (if InternalsVisibleTo not yet added)

**Implementation:**

Register `ISharesConstituentService` in the DI container following the existing `IndexService` pattern. The service uses both `HttpClient` (for iShares API) and `StockAnalyzerDbContext` (for EF Core). Since `StockAnalyzerDbContext` is registered as scoped and the service needs multiple DB operations per invocation, register the service as transient.

In `App.xaml.cs`, add after the existing `IndexService` registration (line 31):
```csharp
services.AddHttpClient<IISharesConstituentService, ISharesConstituentService>();
```

Note: do NOT remove `IndexService` yet — that happens in Phase 2 when the ViewModel is refactored.

Add `InternalsVisibleTo` for test project access to internal parsing methods. In `EodhdLoader.csproj`:
```xml
<ItemGroup>
  <InternalsVisibleTo Include="EodhdLoader.Tests" />
</ItemGroup>
```

**Verification:**
Run: `dotnet build projects/eodhd-loader/EodhdLoader.sln`
Expected: Both main project and test project build successfully

Run: `dotnet test projects/eodhd-loader/tests/EodhdLoader.Tests/`
Expected: All tests pass

**Commit:** `feat(eodhd-loader): register ISharesConstituentService in DI container`
<!-- END_TASK_12 -->
