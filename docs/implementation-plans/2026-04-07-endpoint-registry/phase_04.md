# Endpoint Registry Implementation Plan

**Goal:** Add `endpoints.json` to stock-analyzer, create EndpointRegistry resolver (same pattern as road-trip), and wire Program.cs to resolve all API keys and database connection through the registry.

**Architecture:** Same pointer-file + static resolver pattern as road-trip (Phase 1). EndpointRegistry.cs is copied per-project, not shared via NuGet — repos are independent. All 5 API keys (TwelveData, FMP, Finnhub, EODHD, Marketaux) and the database connection resolve through the registry. Service base URLs are included in endpoints.json as literal entries for documentation and future migration.

**Tech Stack:** C# / .NET 8.0, System.Text.Json, xUnit + FluentAssertions + Moq

**Scope:** 7 phases from original design (this is phase 4 of 7)

**Codebase verified:** 2026-04-07

**Testing reference:** `/home/patrick/projects/stock-analyzer/CLAUDE.md` (project testing conventions)

---

## Acceptance Criteria Coverage

This phase implements and tests:

### endpoint-registry.AC1: Pointer file is single source of truth
- **endpoint-registry.AC1.1 Success:** `endpoints.json` exists at the root of stock-analyzer repo
- **endpoint-registry.AC1.2 Success:** Every remote resource (DB, blob, API) has an entry for each environment (dev, prod)
- **endpoint-registry.AC1.3 Success:** File validates against `endpoints.schema.json` with no errors

### endpoint-registry.AC2: Resolver provides the only path to endpoints
- **endpoint-registry.AC2.1 Success:** `EndpointRegistry.Resolve("database")` returns the correct connection string for the current environment
- **endpoint-registry.AC2.2 Success:** `literal` sources return values directly from the file
- **endpoint-registry.AC2.3 Success:** `env` sources read from environment variables
- **endpoint-registry.AC2.5 Failure:** Missing env var throws descriptive error naming the variable
- **endpoint-registry.AC2.7 Failure:** Unknown endpoint name throws descriptive error listing available endpoints

### endpoint-registry.AC3: No hardcoded connections remain
- **endpoint-registry.AC3.2 Success:** stock-analyzer Program.cs uses `EndpointRegistry.Resolve()` for all API keys and DB

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: Create endpoints.schema.json and endpoints.json for stock-analyzer

**Verifies:** endpoint-registry.AC1.1, endpoint-registry.AC1.2, endpoint-registry.AC1.3

**Files:**
- Create: `/home/patrick/projects/stock-analyzer/endpoints.schema.json` (copy from road-trip — identical schema)
- Create: `/home/patrick/projects/stock-analyzer/endpoints.json`

**Implementation:**

Copy `endpoints.schema.json` from `/home/patrick/projects/road-trip/endpoints.schema.json` — the schema is project-agnostic.

Create `endpoints.json` with all stock-analyzer endpoints. Values confirmed by codebase investigation:

**API keys (confirmed from Program.cs):**
- TwelveData: env `TWELVEDATA_API_KEY` (Program.cs line 64)
- FMP: env `FMP_API_KEY` (Program.cs line 70)
- Finnhub: env `FINNHUB_API_KEY` (Program.cs line 106)
- EODHD: env `EODHD_API_KEY` (EodhdService.cs constructor)
- Marketaux: env `MARKETAUX_API_TOKEN` (Program.cs line 112)

**Base URLs (confirmed from service classes in `/home/patrick/projects/stock-analyzer/src/StockAnalyzer.Core/Services/`):**
- TwelveData: `https://api.twelvedata.com` (TwelveDataService.cs line 21)
- FMP: `https://financialmodelingprep.com/stable` (FmpService.cs line 21)
- Finnhub: `https://finnhub.io/api/v1` (NewsService.cs line 14, SymbolRefreshService.cs line 25)
- EODHD: `https://eodhd.com/api` (EodhdService.cs line 22)
- Marketaux: `https://api.marketaux.com/v1` (MarketauxService.cs line 16)
- Wikipedia: `https://en.wikipedia.org/api/rest_v1/page/summary/` + `https://en.wikipedia.org/w/api.php` (WikipediaService.cs lines 31-32)

**Database:** env `WSL_SQL_CONNECTION` (Program.cs line 132)

```json
{
  "$schema": "./endpoints.schema.json",
  "project": "stock-analyzer",
  "environments": {
    "dev": {
      "database": {
        "source": "env",
        "key": "WSL_SQL_CONNECTION",
        "description": "Stock-analyzer SQL Server (local dev via WSL2)"
      },
      "twelveData": {
        "baseUrl": { "source": "literal", "value": "https://api.twelvedata.com" },
        "apiKey": { "source": "env", "key": "TWELVEDATA_API_KEY" },
        "description": "TwelveData stock data API"
      },
      "fmp": {
        "baseUrl": { "source": "literal", "value": "https://financialmodelingprep.com/stable" },
        "apiKey": { "source": "env", "key": "FMP_API_KEY" },
        "description": "Financial Modeling Prep API"
      },
      "finnhub": {
        "baseUrl": { "source": "literal", "value": "https://finnhub.io/api/v1" },
        "apiKey": { "source": "env", "key": "FINNHUB_API_KEY" },
        "description": "Finnhub stock data and news API"
      },
      "eodhd": {
        "baseUrl": { "source": "literal", "value": "https://eodhd.com/api" },
        "apiKey": { "source": "env", "key": "EODHD_API_KEY" },
        "description": "EODHD historical data API"
      },
      "marketaux": {
        "baseUrl": { "source": "literal", "value": "https://api.marketaux.com/v1" },
        "apiKey": { "source": "env", "key": "MARKETAUX_API_TOKEN" },
        "description": "Marketaux news API"
      },
      "wikipedia": {
        "summaryUrl": { "source": "literal", "value": "https://en.wikipedia.org/api/rest_v1/page/summary/" },
        "searchUrl": { "source": "literal", "value": "https://en.wikipedia.org/w/api.php" },
        "description": "Wikipedia API (public, no auth)"
      }
    },
    "prod": {
      "database": {
        "source": "keyvault",
        "vault": "kv-stk-prod",
        "secret": "DbConnectionString",
        "description": "Azure SQL for stock-analyzer"
      },
      "twelveData": {
        "baseUrl": { "source": "literal", "value": "https://api.twelvedata.com" },
        "apiKey": { "source": "keyvault", "vault": "kv-stk-prod", "secret": "TwelveDataApiKey" },
        "description": "TwelveData stock data API"
      },
      "fmp": {
        "baseUrl": { "source": "literal", "value": "https://financialmodelingprep.com/stable" },
        "apiKey": { "source": "keyvault", "vault": "kv-stk-prod", "secret": "FmpApiKey" },
        "description": "Financial Modeling Prep API"
      },
      "finnhub": {
        "baseUrl": { "source": "literal", "value": "https://finnhub.io/api/v1" },
        "apiKey": { "source": "keyvault", "vault": "kv-stk-prod", "secret": "FinnhubApiKey" },
        "description": "Finnhub stock data and news API"
      },
      "eodhd": {
        "baseUrl": { "source": "literal", "value": "https://eodhd.com/api" },
        "apiKey": { "source": "keyvault", "vault": "kv-stk-prod", "secret": "EodhdApiKey" },
        "description": "EODHD historical data API"
      },
      "marketaux": {
        "baseUrl": { "source": "literal", "value": "https://api.marketaux.com/v1" },
        "apiKey": { "source": "keyvault", "vault": "kv-stk-prod", "secret": "MarketauxApiToken" },
        "description": "Marketaux news API"
      },
      "wikipedia": {
        "summaryUrl": { "source": "literal", "value": "https://en.wikipedia.org/api/rest_v1/page/summary/" },
        "searchUrl": { "source": "literal", "value": "https://en.wikipedia.org/w/api.php" },
        "description": "Wikipedia API (public, no auth)"
      }
    }
  }
}
```

**Note on Yahoo Finance:** The design AC3.3 lists Yahoo as a hardcoded API URL. Yahoo Finance is accessed via the `OoplesFinance.YahooFinanceAPI` NuGet package, which manages its own URLs internally — there is no hardcoded URL or API key in the codebase to migrate. Yahoo is deliberately omitted from endpoints.json.

**Note on Key Vault name:** The value `kv-stk-prod` in the prod entries above is a **placeholder**. The actual Key Vault name is dynamically generated in Bicep as `kv-stk-${shortSuffix}` (where `shortSuffix` = first 6 chars of `uniqueString(resourceGroup().id)`). Before committing, query the actual vault name:

```bash
az keyvault list --resource-group <rg-name> --query "[?starts_with(name, 'kv-stk-')].name" -o tsv
```

Replace all occurrences of `kv-stk-prod` in the prod section with the actual vault name.

**Verification:**

Visual check: every endpoint in both environments, no secrets in file, schema reference correct. Verify Key Vault name matches the deployed vault.

**Commit:** `feat: add endpoint registry schema and pointer file for stock-analyzer`

<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Commit schema and pointer files

**Files:**
- Stage: `/home/patrick/projects/stock-analyzer/endpoints.schema.json`
- Stage: `/home/patrick/projects/stock-analyzer/endpoints.json`

**Step 1: Stage and commit**

```bash
cd /home/patrick/projects/stock-analyzer
git add endpoints.schema.json endpoints.json
git commit -m "feat: add endpoint registry schema and pointer file for stock-analyzer"
```

**Verification:**

Run: `git log -1 --stat`
Expected: 2 files added

<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 3-5) -->

<!-- START_TASK_3 -->
### Task 3: Create EndpointRegistry.cs and update .csproj

**Verifies:** endpoint-registry.AC2.1, endpoint-registry.AC2.2, endpoint-registry.AC2.3, endpoint-registry.AC2.5, endpoint-registry.AC2.7

**Files:**
- Create: `/home/patrick/projects/stock-analyzer/src/StockAnalyzer.Api/EndpointRegistry.cs`
- Modify: `/home/patrick/projects/stock-analyzer/src/StockAnalyzer.Api/StockAnalyzer.Api.csproj`

**Implementation:**

Copy `EndpointRegistry.cs` from road-trip's Phase 1 implementation, changing the namespace from `RoadTripMap` to `StockAnalyzer.Api`. The class is identical in behavior — same static resolver with `Resolve()`, `ValidateAll()`, environment normalization, compound endpoint support, and keyvault resolution (Phase 3 added Azure.Security.KeyVault.Secrets).

Key changes from road-trip version:
- Namespace: `namespace StockAnalyzer.Api;`
- `[assembly: InternalsVisibleTo("StockAnalyzer.Core.Tests")]`

Add NuGet packages to `StockAnalyzer.Api.csproj`:

```xml
<PackageReference Include="Azure.Security.KeyVault.Secrets" Version="4.6.0" />
<PackageReference Include="Azure.Identity" Version="1.13.2" />
```

Add endpoints.json copy to output:

```xml
<ItemGroup>
  <None Include="..\..\endpoints.json" CopyToOutputDirectory="PreserveNewest" Link="endpoints.json" />
</ItemGroup>
```

**Verification:**

Run: `dotnet build /home/patrick/projects/stock-analyzer/src/StockAnalyzer.Api/StockAnalyzer.Api.csproj`
Expected: Build succeeds.

<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Write EndpointRegistry tests

**Verifies:** endpoint-registry.AC2.1, endpoint-registry.AC2.2, endpoint-registry.AC2.3, endpoint-registry.AC2.5, endpoint-registry.AC2.7

**Files:**
- Create: `/home/patrick/projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/EndpointRegistryTests.cs`
- Create: `/home/patrick/projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Fixtures/test-endpoints.json`

**Implementation:**

Same test pattern as road-trip Phase 1 Task 4, adapted for stock-analyzer's namespace and endpoint names.

Create a test-specific `test-endpoints.json` fixture with known entries.

**Testing:**

- **endpoint-registry.AC2.2:** Resolve on a literal source returns the inline value
- **endpoint-registry.AC2.3:** Resolve on an env source reads the env var
- **endpoint-registry.AC2.1:** Resolve("database") with WSL_SQL_CONNECTION set returns the value
- **endpoint-registry.AC2.5:** Resolve on an env source with unset var throws naming the variable
- **endpoint-registry.AC2.7:** Resolve("nonexistent") throws listing available endpoints
- **Compound endpoint:** Resolve("twelveData.apiKey") resolves correctly
- **Environment normalization:** Development→dev, Production→prod

Follow project testing patterns: xUnit `[Fact]`/`[Theory]`, FluentAssertions.

**Verification:**

Run: `dotnet test /home/patrick/projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/ --filter "FullyQualifiedName~EndpointRegistry"`
Expected: All tests pass

<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Run tests and commit resolver

**Step 1: Run all tests**

```bash
cd /home/patrick/projects/stock-analyzer
dotnet test StockAnalyzer.sln
```

Expected: All tests pass.

**Step 2: Commit**

```bash
cd /home/patrick/projects/stock-analyzer
git add src/StockAnalyzer.Api/EndpointRegistry.cs src/StockAnalyzer.Api/StockAnalyzer.Api.csproj tests/StockAnalyzer.Core.Tests/EndpointRegistryTests.cs tests/StockAnalyzer.Core.Tests/Fixtures/test-endpoints.json
git commit -m "feat: add EndpointRegistry resolver with tests for stock-analyzer"
```

<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_B -->

<!-- START_SUBCOMPONENT_C (tasks 6-8) -->

<!-- START_TASK_6 -->
### Task 6: Wire Program.cs database connection through registry

**Verifies:** endpoint-registry.AC3.2 (partially)

**Files:**
- Modify: `/home/patrick/projects/stock-analyzer/src/StockAnalyzer.Api/Program.cs` (lines 132-133)

**Implementation:**

Replace the database connection string resolution (lines 132-133):

```csharp
// BEFORE:
var connectionString = Environment.GetEnvironmentVariable("WSL_SQL_CONNECTION")
    ?? builder.Configuration.GetConnectionString("DefaultConnection");

// AFTER:
var connectionString = EndpointRegistry.Resolve("database");
```

Add `ValidateAll()` after building the app:

```csharp
var app = builder.Build();
EndpointRegistry.ValidateAll();
```

**Verification:**

Run: `dotnet build /home/patrick/projects/stock-analyzer/src/StockAnalyzer.Api/StockAnalyzer.Api.csproj`
Expected: Build succeeds.

<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: Wire Program.cs API keys through registry

**Verifies:** endpoint-registry.AC3.2

**Files:**
- Modify: `/home/patrick/projects/stock-analyzer/src/StockAnalyzer.Api/Program.cs` (multiple locations)

**Implementation:**

Replace each API key resolution in Program.cs with EndpointRegistry calls. All confirmed locations:

**TwelveData (lines ~60-66):**
```csharp
// BEFORE:
var apiKey = config["StockDataProviders:TwelveData:ApiKey"]
          ?? Environment.GetEnvironmentVariable("TWELVEDATA_API_KEY")
          ?? "";

// AFTER:
var apiKey = EndpointRegistry.Resolve("twelveData.apiKey");
```

**FMP (lines ~68-74):**
```csharp
// BEFORE:
var apiKey = config["StockDataProviders:FMP:ApiKey"]
          ?? Environment.GetEnvironmentVariable("FMP_API_KEY")
          ?? "";

// AFTER:
var apiKey = EndpointRegistry.Resolve("fmp.apiKey");
```

**Finnhub (lines ~103-108):**
```csharp
// BEFORE:
var finnhubApiKey = config["Finnhub:ApiKey"]
                  ?? Environment.GetEnvironmentVariable("FINNHUB_API_KEY")
                  ?? "";

// AFTER:
var finnhubApiKey = EndpointRegistry.Resolve("finnhub.apiKey");
```

**Marketaux (lines ~110-114):**
```csharp
// BEFORE:
var marketauxToken = config["Marketaux:ApiToken"]
                   ?? Environment.GetEnvironmentVariable("MARKETAUX_API_TOKEN")
                   ?? "";

// AFTER:
var marketauxToken = EndpointRegistry.Resolve("marketaux.apiKey");
```

**EODHD:** The EODHD API key is read inside `EodhdService` constructor (not in Program.cs). Since EndpointRegistry is in StockAnalyzer.Api and EodhdService is in StockAnalyzer.Core, resolve the key in Program.cs and pass it to the service registration. Find the EodhdService registration in Program.cs and add the resolved key as a constructor parameter or configuration override.

Resolve in Program.cs:
```csharp
var eodhdApiKey = EndpointRegistry.Resolve("eodhd.apiKey");
```

Then update the EodhdService registration to inject this key (e.g., via a factory or by setting the config value that EodhdService reads).

**Verification:**

Run: `dotnet build /home/patrick/projects/stock-analyzer/StockAnalyzer.sln`
Expected: Build succeeds with no errors.

<!-- END_TASK_7 -->

<!-- START_TASK_8 -->
### Task 8: Verify build and tests, commit

**Step 1: Run all tests**

```bash
cd /home/patrick/projects/stock-analyzer
dotnet test StockAnalyzer.sln
```

Expected: All tests pass.

**Step 2: Commit**

```bash
cd /home/patrick/projects/stock-analyzer
git add src/StockAnalyzer.Api/Program.cs
git commit -m "feat: wire stock-analyzer Program.cs to resolve all endpoints through registry"
```

**Verification:**

Run: `git log -3 --oneline`
Expected: Three commits for schema, resolver, and wiring

<!-- END_TASK_8 -->

<!-- END_SUBCOMPONENT_C -->
