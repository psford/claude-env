# Endpoint Registry — Human Test Plan

**Generated:** 2026-04-07
**Implementation plan:** `docs/implementation-plans/2026-04-07-endpoint-registry/`

## Prerequisites

- WSL2 environment with .NET 8 SDK installed
- Azure CLI (`az`) installed and authenticated (`az login`)
- Access to road-trip and stock-analyzer Azure subscriptions
- All automated tests passing:
  - `cd /home/patrick/projects/road-trip && dotnet test tests/RoadTripMap.Tests/ --filter "FullyQualifiedName~EndpointRegistryTests"`
  - `cd /home/patrick/projects/stock-analyzer && dotnet test tests/StockAnalyzer.Core.Tests/ --filter "FullyQualifiedName~EndpointRegistryTests"`

## Phase 1: Road-Trip Local Dev Verification

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | Run `cat /home/patrick/projects/road-trip/endpoints.json \| python3 -m json.tool` | File exists, parses as valid JSON, contains `$schema`, `project`, and `environments` with `dev` and `prod` blocks |
| 1.2 | Verify no hardcoded connection strings remain: `grep -rn "GetEnvironmentVariable.*WSL_SQL_CONNECTION\|GetEnvironmentVariable.*RT_DESIGN_CONNECTION\|Configuration.GetConnectionString" /home/patrick/projects/road-trip/src/ --include="*.cs" \| grep -v EndpointRegistry` | No output (all replaced with EndpointRegistry.Resolve calls) |
| 1.3 | Set `WSL_SQL_CONNECTION` env var and run: `cd /home/patrick/projects/road-trip && dotnet run --project src/RoadTripMap.Web 2>&1 \| head -20` | App starts without endpoint resolution errors; no `InvalidOperationException` in output |
| 1.4 | Open browser to `http://localhost:5000` (or configured port) | Map loads, confirming database and blob storage connections resolved correctly |
| 1.5 | Run seeder without flags: `cd /home/patrick/projects/road-trip && dotnet run --project src/RoadTripMap.PoiSeeder -- --boundaries-only 2>&1 \| head -10` | Seeder starts, connects to local dev database (no Key Vault auth errors) |
| 1.6 | Run seeder with invalid environment: `cd /home/patrick/projects/road-trip && dotnet run --project src/RoadTripMap.PoiSeeder -- --boundaries-only --environment bogus 2>&1 \| head -10` | Error message contains "Unknown environment 'bogus'" and lists "dev, prod" |

## Phase 2: Stock-Analyzer Local Dev Verification

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | Run `cat /home/patrick/projects/stock-analyzer/endpoints.json \| python3 -m json.tool` | File exists, parses as valid JSON, contains `$schema`, `project`, and `environments` with `dev` and `prod` blocks |
| 2.2 | Verify no hardcoded API keys remain: `grep -rn 'GetEnvironmentVariable.*TWELVEDATA_API_KEY\|GetEnvironmentVariable.*FINNHUB_API_KEY\|config\["StockDataProviders' /home/patrick/projects/stock-analyzer/src/ --include="*.cs" \| grep -v EndpointRegistry` | No output |
| 2.3 | Start the stock-analyzer app with dev environment variables set and confirm it starts without endpoint resolution errors | App starts, no `InvalidOperationException` in startup logs |

## Phase 3: Hook Enforcement Verification

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | In a test branch of road-trip, stage a `.cs` file containing `Environment.GetEnvironmentVariable("WSL_SQL_CONNECTION")`. Attempt a commit via Claude Code. | `endpoint_registry_guard.py` fires, prints violation details to stderr, returns exit code 2, commit is blocked |
| 3.2 | In a test branch, modify `endpoints.json` to remove `$schema` key and stage it. Attempt a commit via Claude Code. | `endpoint_schema_validator.py` fires, reports "Missing required top-level key: '$schema'", commit is blocked |
| 3.3 | In a test branch, add a prod literal entry with `"value": "Server=tcp:prod.database.windows.net;Password=hunter2"` to `endpoints.json` and stage it. Attempt a commit. | Schema validator reports "literal value in prod looks like a secret", commit is blocked |
| 3.4 | Stage a clean `.cs` file using `EndpointRegistry.Resolve("database")` and a valid `endpoints.json`. Attempt a commit. | Both hooks return exit 0, commit proceeds |

## Phase 4: Azure Key Vault Verification (Post-Deployment)

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | Run `az keyvault secret list --vault-name kv-roadtripmap-prod --query "[].name" -o tsv` | Output includes `DbConnectionString`, `BlobStorageConnection`, `NpsApiKey` |
| 4.2 | Run `az keyvault secret list --vault-name <kv-stk-XXXXXX> --query "[].name" -o tsv` (replace with actual stock-analyzer vault name) | Output includes `FinnhubApiKey`, `EodhdApiKey`, `TwelveDataApiKey`, `FmpApiKey`, `MarketauxApiToken`, `DbConnectionString` |
| 4.3 | Run `az role assignment list --scope $(az keyvault show --name kv-roadtripmap-prod --query id -o tsv) --query "[?roleDefinitionName=='Key Vault Secrets User']" -o table` | Road-trip App Service managed identity principal ID appears in the results |
| 4.4 | Run the same role assignment check for the stock-analyzer Key Vault | Stock-analyzer App Service managed identity principal ID appears |
| 4.5 | Validate Bicep has no plaintext secrets: `az bicep build --file /home/patrick/projects/road-trip/infrastructure/azure/main.bicep --stdout \| grep -iE "Password=\|AccountKey=" \| grep -v "KeyVault"` | No output (all secrets use @Microsoft.KeyVault references) |
| 4.6 | Same check for stock-analyzer: `az bicep build --file /home/patrick/projects/stock-analyzer/infrastructure/azure/main.bicep --stdout \| grep -iE "Password=\|AccountKey=" \| grep -v "KeyVault"` | No output |

## Phase 5: Production App Verification (Post-Deployment)

| Step | Action | Expected |
|------|--------|----------|
| 5.1 | After deploying road-trip to Azure, check App Service logs: `az webapp log tail --name roadtripmap --resource-group <rg> 2>&1 \| head -50` | No `InvalidOperationException` during startup. `ValidateAll()` completes without errors. |
| 5.2 | Navigate to the production road-trip URL | Map loads, photos display (confirming blob storage resolved), POIs appear (confirming database resolved) |
| 5.3 | After deploying stock-analyzer to Azure, check App Service logs similarly | No endpoint resolution errors during startup |
| 5.4 | Navigate to the production stock-analyzer URL and trigger a stock lookup | Stock data returns (confirming API keys resolved from Key Vault) |

## End-to-End: Secret Leakage Prevention

| Step | Action | Expected |
|------|--------|----------|
| E2E.1 | Create an `endpoints.json` with a prod literal containing `Server=tcp:prod.database.windows.net;Password=realpassword` — confirm schema validator blocks it | AC1.4: blocked |
| E2E.2 | Create a `.cs` file with `Environment.GetEnvironmentVariable("WSL_SQL_CONNECTION")` — confirm registry guard blocks it | AC5.1: blocked |
| E2E.3 | Create an `endpoints.json` with a prod literal containing a 40-character random string (simulating an API key) — confirm schema validator flags it as suspicious | AC1.4: flagged |
| E2E.4 | Verify prod `endpoints.json` entries use only `keyvault` source type for credentials | AC4.3: confirmed |

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| AC1.1 | EndpointRegistryTests (both repos) | 1.1, 2.1 |
| AC1.2 | ValidateAll tests (both repos) | — |
| AC1.3 | endpoint_schema_validator.py | 3.2 |
| AC1.4 | endpoint_schema_validator.py SECRET_PATTERNS | 3.3, E2E.1, E2E.3 |
| AC2.1 | Resolve_EnvSource tests (both repos) | — |
| AC2.2 | Resolve_LiteralSource tests (both repos) | — |
| AC2.3 | Resolve_EnvSource tests (both repos) | — |
| AC2.4 | KeyVault error path test (road-trip) | 5.1, 5.2 (happy path) |
| AC2.5 | MissingVariable tests (both repos) | — |
| AC2.6 | KeyVault descriptive error test (road-trip) | — |
| AC2.7 | UnknownEndpoint tests (both repos) | — |
| AC3.1 | endpoint_registry_guard.py | 1.2 |
| AC3.2 | endpoint_registry_guard.py | 2.2 |
| AC4.1 | None | 4.1 |
| AC4.2 | None | 4.2 |
| AC4.3 | None | 4.5, 4.6 |
| AC4.4 | None | 4.3, 4.4 |
| AC5.1 | endpoint_registry_guard.py | 3.1 |
| AC5.2 | endpoint_schema_validator.py | 3.2 |
| AC5.3 | None (YAML validation) | CI run |
| AC5.4 | None | Push with bad secret name |
| AC6.1 | None | 1.5 |
| AC6.2 | None | 1.6 variant |
| AC6.3 | Environment normalization tests | 5.1 |
| AC6.4 | InvalidEnvironment tests | 1.6 |
