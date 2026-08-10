# Endpoint Registry Implementation Plan

**Goal:** Create the endpoint registry schema, pointer file, and C# resolver for road-trip, then wire database connections through it.

**Architecture:** A committed `endpoints.json` pointer file at the repo root declares all remote resources per environment. A static `EndpointRegistry` class resolves entries by source type (literal, env, keyvault). Application code calls `EndpointRegistry.Resolve()` instead of reading env vars directly.

**Tech Stack:** C# / .NET 8.0, System.Text.Json, xUnit + FluentAssertions + Moq

**Scope:** 7 phases from original design (this is phase 1 of 7)

**Codebase verified:** 2026-04-07

**Testing reference:** `/home/patrick/projects/road-trip/CLAUDE.md` (project testing conventions)

---

## Acceptance Criteria Coverage

This phase implements and tests:

### endpoint-registry.AC1: Pointer file is single source of truth
- **endpoint-registry.AC1.1 Success:** `endpoints.json` exists at the root of road-trip repo
- **endpoint-registry.AC1.2 Success:** Every remote resource (DB, blob, API) has an entry for each environment (dev, prod)
- **endpoint-registry.AC1.3 Success:** File validates against `endpoints.schema.json` with no errors

### endpoint-registry.AC2: Resolver provides the only path to endpoints
- **endpoint-registry.AC2.1 Success:** `EndpointRegistry.Resolve("database")` returns the correct connection string for the current environment
- **endpoint-registry.AC2.2 Success:** `literal` sources return values directly from the file
- **endpoint-registry.AC2.3 Success:** `env` sources read from environment variables
- **endpoint-registry.AC2.5 Failure:** Missing env var throws descriptive error naming the variable
- **endpoint-registry.AC2.7 Failure:** Unknown endpoint name throws descriptive error listing available endpoints

### endpoint-registry.AC3: No hardcoded connections remain
- **endpoint-registry.AC3.1 Success:** road-trip Program.cs and DesignTimeDbContextFactory use `EndpointRegistry.Resolve()` (PoiSeeder addressed in Phase 2)

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: Create endpoints.schema.json and endpoints.json

**Verifies:** endpoint-registry.AC1.1, endpoint-registry.AC1.2, endpoint-registry.AC1.3

**Files:**
- Create: `/home/patrick/projects/road-trip/endpoints.schema.json`
- Create: `/home/patrick/projects/road-trip/endpoints.json`

**Implementation:**

Create `endpoints.schema.json` — a JSON Schema (draft 2020-12) that validates the structure of `endpoints.json`. The schema must enforce:
- Required top-level properties: `$schema`, `project`, `environments`
- Each environment is an object of endpoint entries
- Each endpoint entry is either a simple entry (has `source` property) or a compound entry (has sub-objects with `source` properties, plus optional `description`)
- Simple entry source types: `literal` requires `value`, `env` requires `key`, `keyvault` requires `vault` + `secret`
- `description` is optional on all entries

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Endpoint Registry",
  "description": "Per-project pointer file declaring all remote resources and how to resolve them per environment",
  "type": "object",
  "required": ["$schema", "project", "environments"],
  "additionalProperties": false,
  "properties": {
    "$schema": { "type": "string" },
    "project": { "type": "string" },
    "environments": {
      "type": "object",
      "minProperties": 1,
      "additionalProperties": {
        "type": "object",
        "additionalProperties": {
          "oneOf": [
            { "$ref": "#/$defs/simpleEntry" },
            { "$ref": "#/$defs/compoundEntry" }
          ]
        }
      }
    }
  },
  "$defs": {
    "simpleEntry": {
      "type": "object",
      "required": ["source"],
      "properties": {
        "source": { "enum": ["literal", "env", "keyvault"] },
        "value": { "type": "string" },
        "key": { "type": "string" },
        "vault": { "type": "string" },
        "secret": { "type": "string" },
        "description": { "type": "string" }
      },
      "allOf": [
        {
          "if": { "properties": { "source": { "const": "literal" } }, "required": ["source"] },
          "then": { "required": ["value"] }
        },
        {
          "if": { "properties": { "source": { "const": "env" } }, "required": ["source"] },
          "then": { "required": ["key"] }
        },
        {
          "if": { "properties": { "source": { "const": "keyvault" } }, "required": ["source"] },
          "then": { "required": ["vault", "secret"] }
        }
      ],
      "additionalProperties": false
    },
    "compoundEntry": {
      "type": "object",
      "properties": {
        "description": { "type": "string" }
      },
      "additionalProperties": {
        "oneOf": [
          { "$ref": "#/$defs/simpleEntry" },
          { "type": "string" }
        ]
      },
      "not": {
        "required": ["source"]
      }
    }
  }
}
```

Create `endpoints.json` — the pointer file with all road-trip endpoints for dev and prod environments. Every remote resource the project depends on gets an entry. Values confirmed by codebase investigation:

- `database`: WSL_SQL_CONNECTION env var (dev), Key Vault (prod)
- `database-admin`: RT_DESIGN_CONNECTION env var (dev only — migrations don't run in prod)
- `blobStorage`: Azurite emulator literal (dev), Key Vault (prod)
- `nominatim`: literal URL (same both envs) — currently hardcoded in NominatimGeocodingService.cs:43
- `overpass`: literal URL (same both envs) — currently hardcoded in Program.cs:695
- `padUs`: literal URL (same both envs) — currently hardcoded in PoiSeeder importers
- `npsApi`: compound entry with baseUrl (literal) + apiKey (env/keyvault)

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
      "overpass": {
        "source": "literal",
        "value": "https://overpass-api.de/api/interpreter",
        "description": "Overpass API for OSM queries (public, no auth)"
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
      "overpass": {
        "source": "literal",
        "value": "https://overpass-api.de/api/interpreter",
        "description": "Overpass API (same in all environments)"
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

**Verification:**

Visually verify:
- Every endpoint in both `dev` and `prod` environments
- No actual secret values in the file (only env var names and Key Vault references)
- Schema references point to `./endpoints.schema.json`

**Commit:** `feat: add endpoint registry schema and pointer file for road-trip`

<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Commit schema and pointer files

**Files:**
- Stage: `/home/patrick/projects/road-trip/endpoints.schema.json`
- Stage: `/home/patrick/projects/road-trip/endpoints.json`

**Step 1: Stage and commit**

```bash
cd /home/patrick/projects/road-trip
git add endpoints.schema.json endpoints.json
git commit -m "feat: add endpoint registry schema and pointer file for road-trip"
```

**Verification:**

Run: `git log -1 --stat`
Expected: Commit shows 2 files added

<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 3-5) -->

<!-- START_TASK_3 -->
### Task 3: Create EndpointRegistry.cs and update .csproj

**Verifies:** endpoint-registry.AC2.1, endpoint-registry.AC2.2, endpoint-registry.AC2.3, endpoint-registry.AC2.5, endpoint-registry.AC2.7

**Files:**
- Create: `/home/patrick/projects/road-trip/src/RoadTripMap/EndpointRegistry.cs`
- Modify: `/home/patrick/projects/road-trip/src/RoadTripMap/RoadTripMap.csproj` (add endpoints.json copy)

**Implementation:**

Create `EndpointRegistry.cs` in the `RoadTripMap` namespace. Static class with thread-safe lazy initialization.

Key behaviors:
- `Resolve(string name)` — resolves a single endpoint value. Supports dot notation for compound entries (e.g., `"npsApi.apiKey"`).
- `ValidateAll()` — resolves every endpoint in the current environment, collects all errors, throws `AggregateException` if any fail.
- Environment detection: reads `ASPNETCORE_ENVIRONMENT` → `DOTNET_ENVIRONMENT` → defaults to `"Development"`. Maps `"Development"` → `"dev"`, `"Production"` → `"prod"`.
- File discovery: checks `AppContext.BaseDirectory` first, then walks up from `Directory.GetCurrentDirectory()` to find `endpoints.json`.
- For testability: `internal static string? OverrideFilePath` property and `internal static void Reset()` method allow tests to point at a test-specific JSON file.

Source type resolution:
- `literal` → return `value` property directly
- `env` → read env var named in `key` property; throw `InvalidOperationException` with message `"Environment variable '{key}' not set for endpoint '{name}'"` if missing/empty
- `keyvault` → throw `NotImplementedException("Key Vault resolution is implemented in Phase 3")` (placeholder)

Error for unknown endpoint: throw `InvalidOperationException` with message `"Unknown endpoint '{name}'. Available: {comma-separated list}"`.

Error for unknown environment: throw `InvalidOperationException` with message `"Unknown environment '{env}'. Available: {comma-separated list}"`.

Note: Add `InternalsVisibleTo` to the .csproj instead of the source file (preferred .NET convention):

```xml
<!-- Add to RoadTripMap.csproj -->
<ItemGroup>
  <InternalsVisibleTo Include="RoadTripMap.Tests" />
</ItemGroup>
```

```csharp
using System.Text.Json;

namespace RoadTripMap;

public static class EndpointRegistry
{
    private static JsonDocument? _doc;
    private static readonly object _lock = new();

    internal static string? OverrideFilePath { get; set; }

    internal static void Reset()
    {
        lock (_lock)
        {
            _doc?.Dispose();
            _doc = null;
        }
    }

    public static string Resolve(string name)
    {
        var doc = GetDocument();
        var env = NormalizeEnvironment(GetEnvironment());

        if (!doc.RootElement.TryGetProperty("environments", out var environments))
            throw new InvalidOperationException("endpoints.json missing 'environments' property");

        if (!environments.TryGetProperty(env, out var envBlock))
        {
            var available = string.Join(", ", environments.EnumerateObject().Select(p => p.Name));
            throw new InvalidOperationException($"Unknown environment '{env}'. Available: {available}");
        }

        // Handle dot notation for compound endpoints (e.g., "npsApi.apiKey")
        var parts = name.Split('.', 2);
        var topName = parts[0];

        if (!envBlock.TryGetProperty(topName, out var endpoint))
        {
            var available = string.Join(", ", envBlock.EnumerateObject().Select(p => p.Name));
            throw new InvalidOperationException($"Unknown endpoint '{name}'. Available: {available}");
        }

        if (parts.Length == 2)
        {
            // Compound endpoint — resolve sub-entry
            var subName = parts[1];
            if (!endpoint.TryGetProperty(subName, out var subEntry))
            {
                var available = string.Join(", ",
                    endpoint.EnumerateObject()
                        .Where(p => p.Name != "description")
                        .Select(p => $"{topName}.{p.Name}"));
                throw new InvalidOperationException($"Unknown endpoint '{name}'. Available: {available}");
            }
            return ResolveEntry(subEntry, name);
        }

        // Simple endpoint — must have "source" property
        if (endpoint.TryGetProperty("source", out _))
        {
            return ResolveEntry(endpoint, name);
        }

        // Compound endpoint accessed without sub-key
        var subKeys = string.Join(", ",
            endpoint.EnumerateObject()
                .Where(p => p.Name != "description")
                .Select(p => $"{topName}.{p.Name}"));
        throw new InvalidOperationException(
            $"'{name}' is a compound endpoint. Use a sub-key: {subKeys}");
    }

    public static void ValidateAll()
    {
        var doc = GetDocument();
        var env = NormalizeEnvironment(GetEnvironment());
        var envBlock = doc.RootElement.GetProperty("environments").GetProperty(env);

        var errors = new List<Exception>();

        foreach (var prop in envBlock.EnumerateObject())
        {
            try
            {
                if (prop.Value.TryGetProperty("source", out _))
                {
                    ResolveEntry(prop.Value, prop.Name);
                }
                else
                {
                    // Compound endpoint — resolve each sub-entry
                    foreach (var sub in prop.Value.EnumerateObject())
                    {
                        if (sub.Name == "description") continue;
                        if (sub.Value.ValueKind == JsonValueKind.Object &&
                            sub.Value.TryGetProperty("source", out _))
                        {
                            try
                            {
                                ResolveEntry(sub.Value, $"{prop.Name}.{sub.Name}");
                            }
                            catch (Exception ex)
                            {
                                errors.Add(ex);
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                errors.Add(ex);
            }
        }

        if (errors.Count > 0)
        {
            throw new AggregateException(
                $"Endpoint validation failed with {errors.Count} error(s):\n" +
                string.Join("\n", errors.Select(e => $"  - {e.Message}")),
                errors);
        }
    }

    private static string ResolveEntry(JsonElement entry, string name)
    {
        var source = entry.GetProperty("source").GetString()!;
        return source switch
        {
            "literal" => entry.GetProperty("value").GetString()!,
            "env" => ResolveEnv(entry, name),
            "keyvault" => throw new NotImplementedException(
                $"Key Vault resolution not yet implemented (endpoint '{name}'). See Phase 3."),
            _ => throw new InvalidOperationException(
                $"Unknown source type '{source}' for endpoint '{name}'")
        };
    }

    private static string ResolveEnv(JsonElement entry, string name)
    {
        var key = entry.GetProperty("key").GetString()!;
        var value = Environment.GetEnvironmentVariable(key);
        if (string.IsNullOrEmpty(value))
            throw new InvalidOperationException(
                $"Environment variable '{key}' not set for endpoint '{name}'");
        return value;
    }

    private static JsonDocument GetDocument()
    {
        if (_doc != null) return _doc;
        lock (_lock)
        {
            if (_doc != null) return _doc;
            var path = OverrideFilePath ?? FindEndpointsFile();
            _doc = JsonDocument.Parse(File.ReadAllText(path));
            return _doc;
        }
    }

    private static string FindEndpointsFile()
    {
        // Check output directory first (published apps)
        var binPath = Path.Combine(AppContext.BaseDirectory, "endpoints.json");
        if (File.Exists(binPath)) return binPath;

        // Walk up from current directory (development with dotnet run)
        var dir = Directory.GetCurrentDirectory();
        while (dir != null)
        {
            var candidate = Path.Combine(dir, "endpoints.json");
            if (File.Exists(candidate)) return candidate;
            dir = Path.GetDirectoryName(dir);
        }

        throw new FileNotFoundException(
            "endpoints.json not found. Searched AppContext.BaseDirectory and parent directories from current directory.");
    }

    private static string GetEnvironment()
    {
        return Environment.GetEnvironmentVariable("ASPNETCORE_ENVIRONMENT")
            ?? Environment.GetEnvironmentVariable("DOTNET_ENVIRONMENT")
            ?? "Development";
    }

    private static string NormalizeEnvironment(string env)
    {
        return env.ToLowerInvariant() switch
        {
            "development" => "dev",
            "production" => "prod",
            _ => env.ToLowerInvariant()
        };
    }
}
```

Update `RoadTripMap.csproj` — add an `<ItemGroup>` to copy `endpoints.json` from repo root to the output directory:

```xml
<ItemGroup>
  <None Include="..\..\endpoints.json" CopyToOutputDirectory="PreserveNewest" Link="endpoints.json" />
</ItemGroup>
```

Add this after the existing `<ItemGroup>` blocks in the .csproj file.

**Verification:**

Run: `dotnet build /home/patrick/projects/road-trip/src/RoadTripMap/RoadTripMap.csproj`
Expected: Build succeeds. Check that `endpoints.json` appears in the `bin/Debug/net8.0/` output directory.

<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Write EndpointRegistry tests

**Verifies:** endpoint-registry.AC2.1, endpoint-registry.AC2.2, endpoint-registry.AC2.3, endpoint-registry.AC2.5, endpoint-registry.AC2.7

**Files:**
- Create: `/home/patrick/projects/road-trip/tests/RoadTripMap.Tests/EndpointRegistryTests.cs`
- Create: `/home/patrick/projects/road-trip/tests/RoadTripMap.Tests/Fixtures/test-endpoints.json` (test fixture)

**Implementation:**

Create a test-specific `test-endpoints.json` fixture with known entries for predictable assertions. Include:
- A `dev` environment with: a `literal` entry, an `env` entry, a compound entry
- A `prod` environment with: a `keyvault` entry (for testing the NotImplementedException)

Test class should implement `IDisposable`. In constructor: set `EndpointRegistry.OverrideFilePath` to the test fixture path and call `EndpointRegistry.Reset()`. In `Dispose`: reset both.

**Testing:**

Tests must verify each AC listed above:

- **endpoint-registry.AC2.2:** `Resolve()` on a `literal` source entry returns the inline `value` string directly
- **endpoint-registry.AC2.3:** `Resolve()` on an `env` source entry returns the value of the named environment variable (set a known env var in test setup)
- **endpoint-registry.AC2.1:** `Resolve("database")` with `WSL_SQL_CONNECTION` env var set returns that value (integration of env resolution with the actual endpoint name)
- **endpoint-registry.AC2.5:** `Resolve()` on an `env` source when the env var is not set throws `InvalidOperationException` with message containing the env var name
- **endpoint-registry.AC2.7:** `Resolve("nonexistent")` throws `InvalidOperationException` with message listing available endpoint names
- **Compound endpoint:** `Resolve("npsApi.apiKey")` resolves the sub-entry correctly
- **Compound without sub-key:** `Resolve("npsApi")` throws `InvalidOperationException` listing available sub-keys
- **Unknown environment:** Set `ASPNETCORE_ENVIRONMENT` to an invalid value, verify `Resolve()` throws with available environments listed
- **Environment normalization:** Verify `"Development"` maps to `"dev"` and `"Production"` maps to `"prod"`

Follow project testing patterns: xUnit `[Fact]` and `[Theory]` with `[InlineData]`, FluentAssertions (`.Should().Be()`, `.Should().Throw<>()`).

**Verification:**

Run: `dotnet test /home/patrick/projects/road-trip/tests/RoadTripMap.Tests/ --filter "FullyQualifiedName~EndpointRegistry"`
Expected: All EndpointRegistry tests pass

<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Run tests and commit resolver

**Step 1: Run all tests**

```bash
cd /home/patrick/projects/road-trip
dotnet test RoadTripMap.sln
```

Expected: All tests pass (both new EndpointRegistry tests and existing tests).

**Step 2: Commit**

```bash
git add src/RoadTripMap/EndpointRegistry.cs src/RoadTripMap/RoadTripMap.csproj tests/RoadTripMap.Tests/EndpointRegistryTests.cs tests/RoadTripMap.Tests/Fixtures/test-endpoints.json
git commit -m "feat: add EndpointRegistry resolver with tests"
```

**Verification:**

Run: `git log -1 --stat`
Expected: Commit shows 4 files changed

<!-- END_TASK_5 -->

<!-- END_SUBCOMPONENT_B -->

<!-- START_SUBCOMPONENT_C (tasks 6-7) -->

<!-- START_TASK_6 -->
### Task 6: Wire Program.cs and DesignTimeDbContextFactory.cs to use registry

**Verifies:** endpoint-registry.AC3.1 (partially — PoiSeeder addressed in Phase 2)

**Files:**
- Modify: `/home/patrick/projects/road-trip/src/RoadTripMap/Program.cs` (lines 14-19)
- Modify: `/home/patrick/projects/road-trip/src/RoadTripMap/Data/DesignTimeDbContextFactory.cs` (lines 13-14)

**Implementation:**

In `Program.cs`, replace the existing connection string resolution (lines 14-19):

```csharp
// BEFORE (remove):
var connectionString = Environment.GetEnvironmentVariable("WSL_SQL_CONNECTION")
    ?? builder.Configuration.GetConnectionString("DefaultConnection");
```

```csharp
// AFTER:
var connectionString = EndpointRegistry.Resolve("database");
```

Add `ValidateAll()` call after building the app but before running it. Find the line `var app = builder.Build();` and add after it:

```csharp
EndpointRegistry.ValidateAll();
```

In `DesignTimeDbContextFactory.cs`, replace the existing connection string resolution (lines 13-14):

```csharp
// BEFORE (remove):
var connectionString = Environment.GetEnvironmentVariable("RT_DESIGN_CONNECTION")
    ?? "Server=.\\SQLEXPRESS;Database=RoadTripMap;Trusted_Connection=True;TrustServerCertificate=True";
```

```csharp
// AFTER:
Environment.SetEnvironmentVariable("DOTNET_ENVIRONMENT", "Development");
var connectionString = EndpointRegistry.Resolve("database-admin");
```

Note: The `SetEnvironmentVariable` call ensures the registry uses the `dev` environment when running EF Core CLI tools (which don't set ASPNETCORE_ENVIRONMENT). The Windows SQL Express fallback is removed — developers must set `RT_DESIGN_CONNECTION` in their `.env` file.

**Verification:**

Run: `dotnet build /home/patrick/projects/road-trip/RoadTripMap.sln`
Expected: Build succeeds with no errors

<!-- END_TASK_6 -->

<!-- START_TASK_7 -->
### Task 7: Verify build, tests, and app startup — commit

**Step 1: Run all tests**

```bash
cd /home/patrick/projects/road-trip
dotnet test RoadTripMap.sln
```

Expected: All tests pass.

**Step 2: Verify app starts** (requires WSL_SQL_CONNECTION and NPS_API_KEY env vars set)

```bash
cd /home/patrick/projects/road-trip
source .env 2>/dev/null; dotnet run --project src/RoadTripMap/ &
sleep 3
kill %1
```

Expected: App starts without `InvalidOperationException` from ValidateAll(). If env vars are not set, ValidateAll() will throw — this is correct behavior and confirms the registry is working.

**Step 3: Commit**

```bash
git add src/RoadTripMap/Program.cs src/RoadTripMap/Data/DesignTimeDbContextFactory.cs
git commit -m "feat: wire Program.cs and DesignTimeDbContextFactory to EndpointRegistry"
```

**Verification:**

Run: `git log -2 --oneline`
Expected: Two recent commits for the resolver and wiring

<!-- END_TASK_7 -->

<!-- END_SUBCOMPONENT_C -->
