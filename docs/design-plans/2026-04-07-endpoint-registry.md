# Endpoint Registry Design

## Summary

The endpoint registry is a centralized, per-project configuration system that serves as the single source of truth for every remote resource a project connects to — databases, blob storage, and external APIs. Today, both road-trip and stock-analyzer resolve connection strings and API keys through a mix of direct environment variable reads, hardcoded `appsettings.json` entries, and scattered `Program.cs` lookups, which creates a class of bug where code silently targets the wrong database or uses a stale credential. This design replaces that ad-hoc resolution with a committed `endpoints.json` file in each repo that declares *where* each endpoint's value lives (inline in the file, in an environment variable, or in Azure Key Vault), and a thin `EndpointRegistry` resolver that is the only permitted path for code to obtain a connection string or API key.

The approach separates the map from the secrets: `endpoints.json` is committed to git and contains no sensitive values — it points at the source (an env var name, a Key Vault secret name) rather than embedding the value. Local development continues to use `.env` files via the `env` source type, so no developer workflow changes are required. Production deployments resolve everything through Azure Key Vault, with access granted via managed identity. Enforcement is layered: the resolver validates all endpoints at app startup, pre-commit hooks block new hardcoded connections, and the deploy pipeline confirms that every Key Vault secret referenced in `endpoints.json` actually exists before deploying. The design is rolled out across seven phases, beginning with road-trip and extending to stock-analyzer, then adding enforcement hooks and pipeline validation last so that regression is prevented going forward.

## Definition of Done

This design delivers a per-project parameter file system that is the single source of truth for all remote endpoints (databases, blob storage, APIs — both authenticated and public) across stock-analyzer and road-trip. The param file specifies targets per environment (dev/test/prod), with non-secret dev values inline and all secrets referenced from .env (local) or Azure Key Vault (prod). Build and deploy pipelines enforce that the correct environment's targets are used. As part of this change, all stock-analyzer API keys (TwelveData, FMP, Marketaux) are migrated to Key Vault alongside the existing Finnhub and EODHD entries. The design eliminates hardcoded endpoints, stale env vars, and the class of bug where data is written to the wrong database.

This is not a one-time migration — it establishes the enforced norm for all current and future projects. Any new development that depends on remote APIs, databases, or other external resources must define its targets in a param file. Validation of the param file is a required part of acceptance criteria and testing for every feature that touches external dependencies.

## Acceptance Criteria

### endpoint-registry.AC1: Pointer file is single source of truth
- **endpoint-registry.AC1.1 Success:** `endpoints.json` exists at the root of both road-trip and stock-analyzer repos
- **endpoint-registry.AC1.2 Success:** Every remote resource (DB, blob, API) has an entry for each environment (dev, prod)
- **endpoint-registry.AC1.3 Success:** File validates against `endpoints.schema.json` with no errors
- **endpoint-registry.AC1.4 Failure:** File containing an actual secret is rejected by schema validation

### endpoint-registry.AC2: Resolver provides the only path to endpoints
- **endpoint-registry.AC2.1 Success:** `EndpointRegistry.resolve("database")` returns the correct connection string for the current environment
- **endpoint-registry.AC2.2 Success:** `literal` sources return values directly from the file
- **endpoint-registry.AC2.3 Success:** `env` sources read from environment variables
- **endpoint-registry.AC2.4 Success:** `keyvault` sources fetch from Azure Key Vault
- **endpoint-registry.AC2.5 Failure:** Missing env var throws descriptive error naming the variable
- **endpoint-registry.AC2.6 Failure:** Missing Key Vault secret throws descriptive error naming the vault and secret
- **endpoint-registry.AC2.7 Failure:** Unknown endpoint name throws descriptive error listing available endpoints

### endpoint-registry.AC3: No hardcoded connections remain
- **endpoint-registry.AC3.1 Success:** road-trip Program.cs, PoiSeeder, and DesignTimeDbContextFactory all use `EndpointRegistry.resolve()`
- **endpoint-registry.AC3.2 Success:** stock-analyzer Program.cs uses `EndpointRegistry.resolve()` for all API keys and DB
- **endpoint-registry.AC3.3 Success:** Hardcoded API URLs (Nominatim, Overpass, PAD-US, Yahoo, Wikipedia) moved to `endpoints.json`

### endpoint-registry.AC4: All prod secrets in Key Vault
- **endpoint-registry.AC4.1 Success:** road-trip Key Vault contains DbConnectionString, BlobStorageConnection, NpsApiKey
- **endpoint-registry.AC4.2 Success:** stock-analyzer Key Vault contains all 5 API keys + DbConnectionString
- **endpoint-registry.AC4.3 Success:** Bicep references all secrets via `@Microsoft.KeyVault(...)` — no plaintext
- **endpoint-registry.AC4.4 Success:** App Service managed identities have Key Vault Secrets User role

### endpoint-registry.AC5: Enforcement prevents regression
- **endpoint-registry.AC5.1 Success:** Pre-commit hook blocks hardcoded connection strings outside `endpoints.json`
- **endpoint-registry.AC5.2 Success:** Pre-commit hook validates `endpoints.json` schema on commit
- **endpoint-registry.AC5.3 Success:** Deploy workflow validates all Key Vault secrets exist before deploying
- **endpoint-registry.AC5.4 Failure:** Deploy fails with clear error if referenced Key Vault secret doesn't exist

### endpoint-registry.AC6: Environment selection is explicit and enforced
- **endpoint-registry.AC6.1 Success:** Seeder defaults to dev — running without flags never touches prod
- **endpoint-registry.AC6.2 Success:** Seeder `--environment prod` resolves from prod Key Vault
- **endpoint-registry.AC6.3 Success:** Web app reads environment from ASPNETCORE_ENVIRONMENT
- **endpoint-registry.AC6.4 Failure:** Unrecognized environment name throws with list of valid environments

## Glossary

- **endpoints.json**: The committed pointer file at the root of each repo that declares all remote resources and specifies how to resolve each one per environment. Contains no secrets.
- **endpoints.schema.json**: A JSON Schema file defining the valid structure of `endpoints.json`. Used by hooks and tooling to validate the pointer file on commit.
- **EndpointRegistry**: The thin resolver class (one per tech stack) that reads `endpoints.json`, selects the current environment block, and returns a resolved value. The only permitted call site for obtaining endpoint values.
- **source type**: The resolution strategy for each endpoint entry: `literal` (inline value), `env` (environment variable), or `keyvault` (Azure Key Vault).
- **Azure Key Vault**: Microsoft Azure's managed secrets store. Secrets are stored server-side and accessed at runtime via authenticated API calls.
- **Managed identity**: An Azure-native identity assigned to a service (e.g., App Service) that allows authentication to other Azure resources without credentials in code.
- **Key Vault Secrets User**: The Azure RBAC role granting read access to Key Vault secrets. Assigned to App Service managed identities.
- **Bicep**: Microsoft's infrastructure-as-code language for declaring Azure resources. Used to provision Key Vaults, App Services, and RBAC role assignments.
- **`@Microsoft.KeyVault(...)` reference syntax**: Bicep/ARM syntax instructing Azure to fetch a secret from Key Vault and inject it as an app setting at deploy time.
- **Bicep drift detection**: A pre-deploy step in stock-analyzer's workflow comparing live Azure config against declared Bicep to catch divergence.
- **DesignTimeDbContextFactory**: An EF Core interface providing a `DbContext` at design time for running migrations via CLI, separate from runtime startup.
- **PoiSeeder**: The road-trip console app that seeds point-of-interest data. Currently reads `WSL_SQL_CONNECTION` directly; this design routes it through the registry.
- **Nominatim**: OpenStreetMap's geocoding API for location lookups.
- **PAD-US**: Protected Areas Database of the United States — an ArcGIS service providing park boundary data.
- **validateAll()**: An `EndpointRegistry` method that resolves every declared endpoint at startup, failing fast if any source is unreachable.

## Architecture

### Core Concept: Pointer File, Not Config File

Each project contains an `endpoints.json` at the repo root. This file is committed to git and contains **zero secrets**. For each remote resource the project depends on, it specifies WHERE to find the credential or connection string — never the value itself.

```json
{
  "$schema": "./endpoints.schema.json",
  "project": "road-trip",
  "environments": {
    "dev": {
      "database": {
        "source": "env",
        "key": "WSL_SQL_CONNECTION",
        "description": "Road-trip SQL Server (local dev via WSL2)"
      },
      "database-admin": {
        "source": "env",
        "key": "RT_DESIGN_CONNECTION",
        "description": "Admin connection for EF Core migrations (DDL permissions)"
      },
      "blobStorage": {
        "source": "literal",
        "value": "UseDevelopmentStorage=true",
        "description": "Local Azurite emulator"
      },
      "nominatim": {
        "source": "literal",
        "value": "https://nominatim.openstreetmap.org",
        "description": "Geocoding API (public, no auth)"
      },
      "padUs": {
        "source": "literal",
        "value": "https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US/MapServer/0/query",
        "description": "PAD-US ArcGIS boundary service (public, no auth)"
      },
      "npsApi": {
        "baseUrl": { "source": "literal", "value": "https://developer.nps.gov/api/v1" },
        "apiKey": { "source": "env", "key": "NPS_API_KEY" },
        "description": "National Park Service API"
      }
    },
    "prod": {
      "database": {
        "source": "keyvault",
        "vault": "kv-roadtripmap-prod",
        "secret": "DbConnectionString",
        "description": "Azure SQL (roadtripmap-db on sql-roadtripmap-prod)"
      },
      "blobStorage": {
        "source": "keyvault",
        "vault": "kv-roadtripmap-prod",
        "secret": "BlobStorageConnection",
        "description": "Azure Blob Storage"
      },
      "nominatim": {
        "source": "literal",
        "value": "https://nominatim.openstreetmap.org",
        "description": "Geocoding API (same in all environments)"
      },
      "padUs": {
        "source": "literal",
        "value": "https://edits.nationalmap.gov/arcgis/rest/services/PAD-US/PAD_US/MapServer/0/query",
        "description": "PAD-US ArcGIS boundary service"
      },
      "npsApi": {
        "baseUrl": { "source": "literal", "value": "https://developer.nps.gov/api/v1" },
        "apiKey": { "source": "keyvault", "vault": "kv-roadtripmap-prod", "secret": "NpsApiKey" },
        "description": "National Park Service API"
      }
    }
  }
}
```

### Source Types

| Source | Meaning | When Used |
|--------|---------|-----------|
| `literal` | Value is inline in the file | Public endpoints, non-secret URLs, dev storage emulators |
| `env` | Value is in a named environment variable (from `.env` or shell) | Local dev secrets, WSL connection strings |
| `keyvault` | Value is in Azure Key Vault | All production secrets |

### Resolution Flow

```
Code calls: EndpointRegistry.resolve("database")
  1. Read endpoints.json
  2. Select environment block (from ASPNETCORE_ENVIRONMENT, DOTNET_ENVIRONMENT, or NODE_ENV)
  3. Find "database" entry
  4. Read "source" field:
     - "literal" → return "value" directly
     - "env" → read environment variable named in "key"
     - "keyvault" → fetch from Azure Key Vault using "vault" + "secret"
  5. Return resolved value
  6. If resolution fails → throw with clear error naming the source and key
```

### Resolver Libraries

Each tech stack gets a thin resolver. These are intentionally minimal — read JSON, resolve sources, throw on failure.

**C# (.NET):** `EndpointRegistry` static class in a shared package or per-project utility. Used by Program.cs, seeders, migration factories. Replaces all direct `Environment.GetEnvironmentVariable()` calls for connection strings.

**JavaScript (browser):** Not applicable — browser code never resolves secrets. JS apps call our own API endpoints, which are resolved server-side. The `endpoints.json` file is NOT served to browsers.

**JavaScript (Node/scripts):** Thin resolver for any Node-based tooling or scripts that need endpoint access.

**Python (hooks/scripts):** Resolver for claude-env hooks and utility scripts that query databases or APIs.

### Enforcement Points

| Where | What | How |
|-------|------|-----|
| **App startup** | All endpoints resolve successfully | `EndpointRegistry.validateAll()` called at startup — fails fast if any source is unreachable |
| **Seeder/migration** | Target DB confirmed | Registry resolves "database" for current environment — no ad-hoc env var reads |
| **Deploy pipeline** | Environment matches workflow | GitHub Actions passes environment name; Bicep reads from `endpoints.json` for Key Vault references |
| **Pre-commit hook** | No hardcoded connections | Hook scans staged files for connection string patterns and blocks if found outside `endpoints.json` |
| **Pre-commit hook** | `endpoints.json` is valid | Hook validates JSON schema and checks all referenced env vars/Key Vault secrets are documented |

### Key Vault Integration

**Stock-analyzer currently has:** `FinnhubApiKey`, `EodhdApiKey` in Key Vault (`kv-stk-*`).

**This design adds to stock-analyzer Key Vault:** `TwelveDataApiKey`, `FmpApiKey`, `MarketauxApiToken`, `DbConnectionString`.

**This design creates road-trip Key Vault:** `kv-roadtripmap-prod` with `DbConnectionString`, `BlobStorageConnection`, `NpsApiKey`.

Both Key Vaults grant `Key Vault Secrets User` role to their respective App Service managed identities (pattern already used in stock-analyzer Bicep).

## Existing Patterns

**Connection string resolution:** Both repos use a two-stage pattern: env var → appsettings fallback. Road-trip uses `WSL_SQL_CONNECTION`, stock-analyzer uses the same. This design replaces the ad-hoc env var reads with a single `EndpointRegistry.resolve()` call but preserves `env` as a source type, so existing `.env` files continue to work.

**Key Vault references in Bicep:** Stock-analyzer already uses `@Microsoft.KeyVault(VaultName=...;SecretName=...)` syntax for Finnhub and EODHD. This design extends that pattern to all secrets and adds it to road-trip.

**Bicep drift detection:** Stock-analyzer's deploy workflow has a pre-deploy step comparing live Azure config to declared Bicep. This design leverages that — `endpoints.json` becomes the source that Bicep reads from, and drift detection validates both match.

**Divergence from existing:** Currently, each codebase has its own ad-hoc connection resolution scattered across Program.cs, DesignTimeDbContextFactory, and seeder Program.cs. This design consolidates to a single entry point. The existing appsettings.json files become thin (just `ASPNETCORE_ENVIRONMENT` selection) — all endpoint values move to `endpoints.json`.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Schema and Resolver (road-trip)
**Goal:** Define `endpoints.json` schema, create C# resolver, wire into road-trip web app

**Components:**
- `endpoints.schema.json` at repo root — JSON Schema for validation
- `endpoints.json` at repo root — road-trip endpoint definitions for dev and prod
- `EndpointRegistry.cs` in `src/RoadTripMap/` — static resolver class (resolve, validateAll)
- Update `src/RoadTripMap/Program.cs` — replace `WSL_SQL_CONNECTION` reads with `EndpointRegistry.resolve("database")`
- Update `src/RoadTripMap/Data/DesignTimeDbContextFactory.cs` — use `EndpointRegistry.resolve("database-admin")`

**Dependencies:** None (first phase)

**Done when:** App starts, resolves all endpoints from `endpoints.json` using `env` sources in dev, existing tests pass
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Seeder and Migration Integration (road-trip)
**Goal:** Seeder and migration scripts use the registry instead of direct env var reads

**Components:**
- Update `src/RoadTripMap.PoiSeeder/Program.cs` — use `EndpointRegistry.resolve("database")` instead of `WSL_SQL_CONNECTION`
- Remove `--confirm-remote` flag (no longer needed — the registry determines the target based on environment)
- Environment selection: seeder reads `DOTNET_ENVIRONMENT` (default: `dev`)
- `--environment prod` CLI flag overrides for explicit prod targeting

**Dependencies:** Phase 1

**Done when:** `dotnet run --project PoiSeeder -- --boundaries-only` resolves DB from registry; `dotnet run --project PoiSeeder -- --boundaries-only --environment prod` resolves from prod Key Vault; no direct env var reads remain in seeder
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Key Vault Setup (road-trip)
**Goal:** Create road-trip Key Vault, migrate secrets from Bicep inline to Key Vault references

**Components:**
- Update `infrastructure/azure/main.bicep` — add Key Vault resource, store `DbConnectionString` and `BlobStorageConnection` as secrets, reference via `@Microsoft.KeyVault(...)` in app settings
- Add `NpsApiKey` to Key Vault
- Grant App Service managed identity `Key Vault Secrets User` role
- Update `endpoints.json` prod section with vault name and secret names

**Dependencies:** Phase 1

**Done when:** Deploy workflow provisions Key Vault, app reads secrets from vault at startup, no plaintext secrets in Bicep app settings
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Schema and Resolver (stock-analyzer)
**Goal:** Add `endpoints.json` to stock-analyzer, create resolver, wire into app

**Components:**
- `endpoints.json` at stock-analyzer repo root — all endpoints (DB, TwelveData, FMP, Finnhub, EODHD, Marketaux, Yahoo, Wikipedia)
- `EndpointRegistry.cs` in stock-analyzer — same resolver pattern as road-trip (shared via copy, not shared library — repos are independent)
- Update `src/StockAnalyzer.Api/Program.cs` — replace all `config["...ApiKey"]` and env var reads with registry calls

**Dependencies:** Phase 1 (pattern established)

**Done when:** Stock-analyzer resolves all endpoints from registry, existing tests pass
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Key Vault Migration (stock-analyzer)
**Goal:** Move remaining API keys to Key Vault (TwelveData, FMP, Marketaux)

**Components:**
- Update `infrastructure/azure/main.bicep` — add `TwelveDataApiKey`, `FmpApiKey`, `MarketauxApiToken` as Key Vault secrets, reference in app settings
- Update `endpoints.json` prod section with new vault secret names
- Verify existing Finnhub and EODHD Key Vault references still work

**Dependencies:** Phase 4

**Done when:** All 5 API keys in Key Vault, no plaintext API keys in Bicep, deploy succeeds with smoke tests passing
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Enforcement Hooks
**Goal:** Prevent regression — block hardcoded connections and validate registry file

**Components:**
- `endpoint_registry_guard.py` in claude-env hooks — blocks git commit when staged files contain hardcoded connection strings, direct `Environment.GetEnvironmentVariable()` calls for known endpoint keys, or `appsettings` connection string patterns outside `endpoints.json`
- `endpoint_schema_validator.py` in claude-env hooks — validates `endpoints.json` against schema on commit, checks all `env` sources have corresponding `.env` documentation, checks all `keyvault` sources reference valid vault/secret names
- Register both hooks in `settings.local.json`

**Dependencies:** Phases 1-5 (all repos migrated first)

**Done when:** Committing a hardcoded connection string is blocked, committing invalid `endpoints.json` is blocked
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: Deploy Pipeline Integration
**Goal:** Deploy workflows read environment from `endpoints.json` and validate before deploying

**Components:**
- Update road-trip `.github/workflows/deploy.yml` — pre-deploy step validates `endpoints.json` prod section, confirms Key Vault secrets exist via `az keyvault secret show`
- Update stock-analyzer `.github/workflows/azure-deploy.yml` — same validation step
- Extend existing Bicep drift detection (stock-analyzer) to include `endpoints.json` validation

**Dependencies:** Phases 3, 5 (Key Vault set up), Phase 6 (hooks)

**Done when:** Deploy fails if `endpoints.json` references a Key Vault secret that doesn't exist, deploy passes when all secrets are present
<!-- END_PHASE_7 -->

## Additional Considerations

**Environment discovery:** The resolver determines the current environment from `ASPNETCORE_ENVIRONMENT` (C# web apps), `DOTNET_ENVIRONMENT` (C# console apps/seeders), or `NODE_ENV` (JavaScript). Default is `dev`. Production Azure App Services already set `ASPNETCORE_ENVIRONMENT=Production`.

**No shared library:** The resolver is copied per-project, not shared via NuGet. The repos are independent — a shared library creates a coupling and versioning burden that isn't justified for a ~100-line utility class.

**Key Vault access in dev:** Developers don't need Key Vault access for local dev — all dev entries use `env` or `literal` sources. Key Vault is only resolved when environment is `prod` (or `staging` if added later).

**Migration path:** Existing `.env` files continue to work. The registry reads from them via `env` source type. No breaking change to developer workflow — just a new indirection layer that prevents the wrong-database class of bugs.

**T-Tracker and future projects:** Non-.NET projects (plain HTML/JS/CSS) that need API keys use the same `endpoints.json` format. A build step or server-side proxy resolves the key. The browser never sees the registry file or any secrets.
