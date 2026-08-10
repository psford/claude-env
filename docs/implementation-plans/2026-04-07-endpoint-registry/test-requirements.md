# Endpoint Registry Test Requirements

Maps each acceptance criterion to an automated test or documented human verification.

---

## AC1: Pointer file is single source of truth

### endpoint-registry.AC1.1 Success
**Criterion:** `endpoints.json` exists at the root of both road-trip and stock-analyzer repos.

| Field | Value |
|-------|-------|
| Test type | Unit |
| Test file (road-trip) | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Test file (stock-analyzer) | `tests/StockAnalyzer.Core.Tests/EndpointRegistryTests.cs` |
| Approach | EndpointRegistry tests load `endpoints.json` (via `OverrideFilePath` pointing at `Fixtures/test-endpoints.json`) and verify it parses successfully. Phase 1 Task 4 and Phase 4 Task 4 each include a test that `Resolve()` returns values from the file, which implicitly proves the file exists and is loadable. Additionally, the `.csproj` `CopyToOutputDirectory` directive is verified by `dotnet build` producing the file in `bin/Debug/net8.0/`. |

---

### endpoint-registry.AC1.2 Success
**Criterion:** Every remote resource (DB, blob, API) has an entry for each environment (dev, prod).

| Field | Value |
|-------|-------|
| Test type | Unit |
| Test file (road-trip) | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Test file (stock-analyzer) | `tests/StockAnalyzer.Core.Tests/EndpointRegistryTests.cs` |
| Approach | `ValidateAll()` resolves every endpoint in the current environment block. A test sets environment to `dev` and calls `ValidateAll()` with all required env vars set. If any endpoint is missing from the JSON, the test fails. A second test (or `[Theory]` with `[InlineData]`) verifies the `prod` environment block exists and contains entries (the keyvault resolution will throw `NotImplementedException` or `AuthenticationFailedException`, confirming the entries are present even though they cannot resolve in test). |

---

### endpoint-registry.AC1.3 Success
**Criterion:** File validates against `endpoints.schema.json` with no errors.

| Field | Value |
|-------|-------|
| Test type | Unit (Python) |
| Test file | `.claude/hooks/endpoint_schema_validator.py` (self-validates when invoked) |
| Approach | Phase 6 `endpoint_schema_validator.py` performs structural validation of `endpoints.json` against the schema rules (required keys, source types, required fields per source type). Tested by: (1) running the validator script against each repo's `endpoints.json` during Phase 6 Task 2 verification, and (2) unit-style invocation with synthetic valid/invalid JSON to confirm pass/fail. The validator is standard-library Python and does not depend on the `jsonschema` package. |

---

### endpoint-registry.AC1.4 Failure
**Criterion:** File containing an actual secret is rejected by schema validation.

| Field | Value |
|-------|-------|
| Test type | Unit (Python) |
| Test file | `.claude/hooks/endpoint_schema_validator.py` |
| Approach | The validator's secret detection logic scans `literal` values in `prod` environment blocks for connection string patterns (`Server=...Password=`), `AccountKey=`, `DefaultEndpointsProtocol=`, known secret prefixes (`sk-`, `pk-`), and suspicious long random strings (>30 chars, non-URL). Test by piping a crafted `endpoints.json` with a literal prod entry containing `Server=tcp:...;Password=hunter2` and confirming exit code 2 with an error message naming the offending entry. |

---

## AC2: Resolver provides the only path to endpoints

### endpoint-registry.AC2.1 Success
**Criterion:** `EndpointRegistry.Resolve("database")` returns the correct connection string for the current environment.

| Field | Value |
|-------|-------|
| Test type | Unit |
| Test file (road-trip) | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Test file (stock-analyzer) | `tests/StockAnalyzer.Core.Tests/EndpointRegistryTests.cs` |
| Approach | Set `ASPNETCORE_ENVIRONMENT=Development`, set `WSL_SQL_CONNECTION` to a known test value, point `OverrideFilePath` at `test-endpoints.json` (which has a `dev.database` entry with `source: env`, `key: WSL_SQL_CONNECTION`). Assert `Resolve("database")` returns the known value. xUnit `[Fact]`, FluentAssertions `.Should().Be()`. |

---

### endpoint-registry.AC2.2 Success
**Criterion:** `literal` sources return values directly from the file.

| Field | Value |
|-------|-------|
| Test type | Unit |
| Test file (road-trip) | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Test file (stock-analyzer) | `tests/StockAnalyzer.Core.Tests/EndpointRegistryTests.cs` |
| Approach | `test-endpoints.json` includes a `literal` entry (e.g., `nominatim` with inline URL). Test calls `Resolve("nominatim")` and asserts the returned string matches the inline `value` exactly. |

---

### endpoint-registry.AC2.3 Success
**Criterion:** `env` sources read from environment variables.

| Field | Value |
|-------|-------|
| Test type | Unit |
| Test file (road-trip) | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Test file (stock-analyzer) | `tests/StockAnalyzer.Core.Tests/EndpointRegistryTests.cs` |
| Approach | Set a known env var in test setup (e.g., `Environment.SetEnvironmentVariable("TEST_DB_CONN", "Server=test")`). `test-endpoints.json` has an `env` entry pointing at `TEST_DB_CONN`. Test calls `Resolve()` and asserts the returned value matches `"Server=test"`. Cleanup in `Dispose()`. |

---

### endpoint-registry.AC2.4 Success
**Criterion:** `keyvault` sources fetch from Azure Key Vault.

| Field | Value |
|-------|-------|
| Test type | Unit (error path) + Human verification (happy path) |
| Test file | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Approach (unit) | `test-endpoints.json` includes a `prod` environment with a keyvault entry pointing to a non-existent vault. Set environment to `prod`, call `Resolve()`, and verify the error message contains the vault name and secret name. This confirms the code path reaches Key Vault resolution and constructs the `SecretClient` correctly. |
| Approach (human) | After Phase 3 deployment, verify the app starts in Azure and reads secrets from Key Vault by checking App Service logs for successful `ValidateAll()` completion with no `InvalidOperationException`. |
| Justification for human verification | The happy path requires a live Azure Key Vault with managed identity authentication. Unit tests cannot provision Azure infrastructure. The deploy pipeline smoke test (Phase 7) provides partial automation. |

---

### endpoint-registry.AC2.5 Failure
**Criterion:** Missing env var throws descriptive error naming the variable.

| Field | Value |
|-------|-------|
| Test type | Unit |
| Test file (road-trip) | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Test file (stock-analyzer) | `tests/StockAnalyzer.Core.Tests/EndpointRegistryTests.cs` |
| Approach | Ensure the target env var is not set (`Environment.SetEnvironmentVariable("MISSING_VAR", null)`). `test-endpoints.json` has an `env` entry with `key: MISSING_VAR`. Call `Resolve()` and assert it throws `InvalidOperationException` with message containing both the env var name (`MISSING_VAR`) and the endpoint name. FluentAssertions `.Should().Throw<InvalidOperationException>().WithMessage("*MISSING_VAR*")`. |

---

### endpoint-registry.AC2.6 Failure
**Criterion:** Missing Key Vault secret throws descriptive error naming the vault and secret.

| Field | Value |
|-------|-------|
| Test type | Unit |
| Test file | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Approach | Set environment to `prod`. `test-endpoints.json` has a keyvault entry with `vault: fake-vault-name`, `secret: FakeSecret`. Call `Resolve()` and catch the `InvalidOperationException`. Assert the error message contains both `"fake-vault-name"` and `"FakeSecret"`. The test verifies the error wrapping in the `catch (Azure.RequestFailedException)` and `catch (Azure.Identity.AuthenticationFailedException)` paths, since no real vault exists. |

---

### endpoint-registry.AC2.7 Failure
**Criterion:** Unknown endpoint name throws descriptive error listing available endpoints.

| Field | Value |
|-------|-------|
| Test type | Unit |
| Test file (road-trip) | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Test file (stock-analyzer) | `tests/StockAnalyzer.Core.Tests/EndpointRegistryTests.cs` |
| Approach | Call `Resolve("nonexistent")` against `test-endpoints.json`. Assert it throws `InvalidOperationException` with message containing `"nonexistent"` and listing at least one known endpoint name from the fixture (e.g., `"database"`, `"nominatim"`). |

---

## AC3: No hardcoded connections remain

### endpoint-registry.AC3.1 Success
**Criterion:** road-trip Program.cs, PoiSeeder, and DesignTimeDbContextFactory all use `EndpointRegistry.Resolve()`.

| Field | Value |
|-------|-------|
| Test type | Operational (code inspection) + Unit (hook enforcement) |
| Test file | `.claude/hooks/endpoint_registry_guard.py` |
| Approach (operational) | After Phase 1 Task 6 and Phase 2 Task 2, verify by grep that no direct `GetEnvironmentVariable("WSL_SQL_CONNECTION")`, `GetEnvironmentVariable("RT_DESIGN_CONNECTION")`, or `Configuration.GetConnectionString(` calls remain in `Program.cs`, `PoiSeeder/Program.cs`, or `DesignTimeDbContextFactory.cs`. This is a one-time migration verification done during implementation. |
| Approach (automated) | Phase 6 `endpoint_registry_guard.py` hook blocks future commits containing direct env var reads for known endpoint keys in non-excluded files. This prevents regression after the initial migration. |

---

### endpoint-registry.AC3.2 Success
**Criterion:** stock-analyzer Program.cs uses `EndpointRegistry.Resolve()` for all API keys and DB.

| Field | Value |
|-------|-------|
| Test type | Operational (code inspection) + Unit (hook enforcement) |
| Test file | `.claude/hooks/endpoint_registry_guard.py` |
| Approach (operational) | After Phase 4 Tasks 6-7, verify by grep that no direct `GetEnvironmentVariable("TWELVEDATA_API_KEY")`, `config["StockDataProviders:..."]`, etc. remain in `Program.cs`. One-time migration verification. |
| Approach (automated) | Phase 6 hook prevents regression by blocking future commits with direct env var reads for any key listed in `endpoints.json`. |

---

### endpoint-registry.AC3.3 Success
**Criterion:** Hardcoded API URLs (Nominatim, Overpass, PAD-US, Yahoo, Wikipedia) moved to `endpoints.json`.

| Field | Value |
|-------|-------|
| Test type | Operational (code inspection) + Unit (hook enforcement) |
| Test file | `.claude/hooks/endpoint_registry_guard.py` |
| Approach (operational) | After implementation, verify that hardcoded URLs in `NominatimGeocodingService.cs`, `PoiSeeder/Program.cs` (Overpass), PAD-US importers, and `WikipediaService.cs` are replaced with `EndpointRegistry.Resolve()` calls. Yahoo Finance uses the `OoplesFinance.YahooFinanceAPI` NuGet package which manages its own URLs — no migration needed. |
| Approach (automated) | The endpoint registry guard hook does not scan for hardcoded URLs (only connection strings and known env var reads). URL migration is enforced by code review convention, not automated testing. |

---

## AC4: All prod secrets in Key Vault

### endpoint-registry.AC4.1 Success
**Criterion:** road-trip Key Vault contains DbConnectionString, BlobStorageConnection, NpsApiKey.

| Field | Value |
|-------|-------|
| Test type | Human verification |
| Justification | Requires live Azure infrastructure. Key Vault secrets are provisioned by Bicep deployment — cannot be validated without running `az deployment group create` against a real subscription. |
| Verification approach | After Phase 3 deployment: `az keyvault secret list --vault-name kv-roadtripmap-prod --query "[].name" -o tsv`. Confirm output includes `DbConnectionString`, `BlobStorageConnection`, `NpsApiKey`. The Phase 7 deploy pipeline validation step automates this check for subsequent deploys. |

---

### endpoint-registry.AC4.2 Success
**Criterion:** stock-analyzer Key Vault contains all 5 API keys + DbConnectionString.

| Field | Value |
|-------|-------|
| Test type | Human verification |
| Justification | Requires live Azure infrastructure with deployed Key Vault. |
| Verification approach | After Phase 5 deployment: `az keyvault secret list --vault-name <kv-stk-XXXXXX> --query "[].name" -o tsv`. Confirm output includes `FinnhubApiKey`, `EodhdApiKey`, `TwelveDataApiKey`, `FmpApiKey`, `MarketauxApiToken`, `DbConnectionString`. The Phase 7 deploy pipeline validation step automates this for subsequent deploys. |

---

### endpoint-registry.AC4.3 Success
**Criterion:** Bicep references all secrets via `@Microsoft.KeyVault(...)` -- no plaintext.

| Field | Value |
|-------|-------|
| Test type | Operational |
| Test approach | `az bicep build --file infrastructure/azure/main.bicep` validates Bicep syntax in both repos. Additionally, grep the compiled ARM template (output of `az bicep build`) for any remaining plaintext connection strings or API keys in the `appSettings` and `connectionStrings` sections. All credential app settings must use the `@Microsoft.KeyVault(VaultName=...;SecretName=...)` pattern. |
| Verification commands | Road-trip: `az bicep build --file /home/patrick/projects/road-trip/infrastructure/azure/main.bicep`; Stock-analyzer: `az bicep build --file /home/patrick/projects/stock-analyzer/infrastructure/azure/main.bicep`. Then grep output for `Password=`, `AccountKey=`, or any `ApiKey` value that is not a Key Vault reference. |

---

### endpoint-registry.AC4.4 Success
**Criterion:** App Service managed identities have Key Vault Secrets User role.

| Field | Value |
|-------|-------|
| Test type | Human verification |
| Justification | Requires live Azure infrastructure. Role assignments are declared in Bicep but only verifiable after deployment against a real subscription. |
| Verification approach | After deployment: `az role assignment list --scope $(az keyvault show --name <vault-name> --query id -o tsv) --query "[?roleDefinitionName=='Key Vault Secrets User']" -o table`. Confirm the App Service managed identity principal ID appears. |

---

## AC5: Enforcement prevents regression

### endpoint-registry.AC5.1 Success
**Criterion:** Pre-commit hook blocks hardcoded connection strings outside `endpoints.json`.

| Field | Value |
|-------|-------|
| Test type | Unit (Python) |
| Test file | `.claude/hooks/endpoint_registry_guard.py` |
| Approach | Invoke the hook script with crafted stdin JSON simulating a `git commit` command. Set up a git repo with `endpoints.json` and stage a `.cs` file containing `GetEnvironmentVariable("WSL_SQL_CONNECTION")`. Pipe the hook input and assert exit code 2 with stderr containing the violation description. Also test the clean case (file using `EndpointRegistry.Resolve()`) returns exit 0. |
| Verification commands | `echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' \| python .claude/hooks/endpoint_registry_guard.py` (from a repo with endpoints.json and staged violations). |

---

### endpoint-registry.AC5.2 Success
**Criterion:** Pre-commit hook validates `endpoints.json` schema on commit.

| Field | Value |
|-------|-------|
| Test type | Unit (Python) |
| Test file | `.claude/hooks/endpoint_schema_validator.py` |
| Approach | Invoke the validator with crafted stdin JSON simulating a `git commit` command. Set up a git repo where `endpoints.json` is staged. Test cases: (1) valid file returns exit 0, (2) file missing `$schema` key returns exit 2, (3) `literal` entry missing `value` returns exit 2, (4) `env` entry missing `key` returns exit 2, (5) `keyvault` entry missing `vault` returns exit 2. |

---

### endpoint-registry.AC5.3 Success
**Criterion:** Deploy workflow validates all Key Vault secrets exist before deploying.

| Field | Value |
|-------|-------|
| Test type | Operational |
| Test approach | Validate deploy workflow YAML syntax: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/deploy.yml'))"` in each repo. The validation step itself runs in GitHub Actions with Azure credentials and calls `az keyvault secret show` for each prod keyvault entry parsed from `endpoints.json`. Full validation requires a CI run against live infrastructure. |
| Verification commands | Road-trip: `python3 -c "import yaml; yaml.safe_load(open('/home/patrick/projects/road-trip/.github/workflows/deploy.yml'))"`. Stock-analyzer: `python3 -c "import yaml; yaml.safe_load(open('/home/patrick/projects/stock-analyzer/.github/workflows/azure-deploy.yml'))"`. |

---

### endpoint-registry.AC5.4 Failure
**Criterion:** Deploy fails with clear error if referenced Key Vault secret doesn't exist.

| Field | Value |
|-------|-------|
| Test type | Operational (CI run) |
| Test approach | Trigger a deploy workflow run with an `endpoints.json` that references a non-existent Key Vault secret name. The workflow validation step should fail with `::error::Key Vault secret 'NonExistent' not found in vault '...'` and exit code 1, blocking the deploy. Verified by inspecting the GitHub Actions run log. |
| Justification for operational | Requires GitHub Actions runner with Azure credentials and access to the actual Key Vault. Cannot be unit tested locally without mocking the entire `az` CLI and GitHub Actions environment. |

---

## AC6: Environment selection is explicit and enforced

### endpoint-registry.AC6.1 Success
**Criterion:** Seeder defaults to dev -- running without flags never touches prod.

| Field | Value |
|-------|-------|
| Test type | Integration |
| Test file | Operational verification during Phase 2 Task 3 |
| Approach | Run `dotnet run --project src/RoadTripMap.PoiSeeder -- --boundaries-only` without any `--environment` flag. Verify via console output or debugger that `DOTNET_ENVIRONMENT` resolves to `Development` and the registry selects the `dev` environment block. The seeder should attempt to connect to the local dev database (via `WSL_SQL_CONNECTION` env var), never the prod Key Vault. |
| Verification commands | `dotnet run --project /home/patrick/projects/road-trip/src/RoadTripMap.PoiSeeder -- --boundaries-only 2>&1 \| head -5` (should not show Key Vault authentication errors). |

---

### endpoint-registry.AC6.2 Success
**Criterion:** Seeder `--environment prod` resolves from prod Key Vault.

| Field | Value |
|-------|-------|
| Test type | Integration |
| Test file | Operational verification during Phase 2 Task 3 |
| Approach | Run `dotnet run --project src/RoadTripMap.PoiSeeder -- --boundaries-only --environment prod`. The registry should attempt Key Vault resolution. Without local Azure credentials, it will throw an `AuthenticationFailedException` — this is the expected behavior and confirms the prod path is active. With credentials configured (`az login`), it should successfully resolve from Key Vault. |
| Verification commands | `dotnet run --project /home/patrick/projects/road-trip/src/RoadTripMap.PoiSeeder -- --boundaries-only --environment prod 2>&1 \| head -5` (expect Key Vault auth error or successful resolution depending on credentials). |

---

### endpoint-registry.AC6.3 Success
**Criterion:** Web app reads environment from ASPNETCORE_ENVIRONMENT.

| Field | Value |
|-------|-------|
| Test type | Operational (Bicep inspection) + Unit |
| Test file | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Approach (unit) | Set `ASPNETCORE_ENVIRONMENT=Production`, verify `Resolve()` selects the `prod` environment block (will fail on keyvault resolution, but the environment selection is confirmed by the error message referencing a prod vault name). Set `ASPNETCORE_ENVIRONMENT=Development`, verify `Resolve()` selects `dev`. |
| Approach (operational) | Verify both repos' `main.bicep` files include `ASPNETCORE_ENVIRONMENT` in the App Service app settings. Road-trip: grep for `ASPNETCORE_ENVIRONMENT` in `infrastructure/azure/main.bicep`. Stock-analyzer: same. Phase 7 Task 3 performs this verification. |

---

### endpoint-registry.AC6.4 Failure
**Criterion:** Unrecognized environment name throws with list of valid environments.

| Field | Value |
|-------|-------|
| Test type | Unit + Integration |
| Test file | `tests/RoadTripMap.Tests/EndpointRegistryTests.cs` |
| Approach (unit) | Set `ASPNETCORE_ENVIRONMENT` to `"bogus"`. Call `Resolve("database")`. Assert throws `InvalidOperationException` with message containing `"bogus"` and listing available environments (e.g., `"dev, prod"`). |
| Approach (integration) | Run seeder with `--environment bogus`: `dotnet run --project src/RoadTripMap.PoiSeeder -- --boundaries-only --environment bogus 2>&1 \| head -5`. Expect error output listing valid environments. Phase 2 Task 3 Step 3 performs this verification. |

---

## Test Execution Summary

### Automated tests by phase

| Phase | Test type | Location | Runner |
|-------|-----------|----------|--------|
| Phase 1 | xUnit unit tests | `road-trip/tests/RoadTripMap.Tests/EndpointRegistryTests.cs` | `dotnet test` |
| Phase 3 | Bicep validation | `road-trip/infrastructure/azure/main.bicep` | `az bicep build` |
| Phase 4 | xUnit unit tests | `stock-analyzer/tests/StockAnalyzer.Core.Tests/EndpointRegistryTests.cs` | `dotnet test` |
| Phase 5 | Bicep validation | `stock-analyzer/infrastructure/azure/main.bicep` | `az bicep build` |
| Phase 6 | Python hook tests | `.claude/hooks/endpoint_registry_guard.py`, `endpoint_schema_validator.py` | `python` + stdin piping |
| Phase 7 | YAML validation | `.github/workflows/deploy.yml`, `azure-deploy.yml` | `python -c "import yaml; ..."` |

### Human verification items

| Criterion | Requires | When to verify |
|-----------|----------|----------------|
| AC2.4 (happy path) | Live Azure Key Vault + managed identity | After Phase 3 first deployment |
| AC4.1 | Live road-trip Key Vault | After Phase 3 first deployment |
| AC4.2 | Live stock-analyzer Key Vault | After Phase 5 first deployment |
| AC4.4 | Live RBAC role assignments | After Phase 3 and Phase 5 first deployments |
| AC5.4 | GitHub Actions with Azure credentials | After Phase 7 first deploy workflow run |

All human verification items become automated after Phase 7, when the deploy pipeline validation step runs `az keyvault secret show` against live infrastructure on every subsequent deploy.
