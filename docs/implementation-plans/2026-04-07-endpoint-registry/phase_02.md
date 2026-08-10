# Endpoint Registry Implementation Plan

**Goal:** Wire the road-trip PoiSeeder through the EndpointRegistry, add explicit environment selection via `--environment` flag, and remove the legacy `--confirm-remote` safety check.

**Architecture:** The seeder uses the same `EndpointRegistry` resolver from Phase 1 (accessible via ProjectReference to RoadTripMap). Environment defaults to `dev` via `DOTNET_ENVIRONMENT`, with an explicit `--environment` CLI override for targeting prod.

**Tech Stack:** C# / .NET 8.0, System.Text.Json, xUnit + FluentAssertions

**Scope:** 7 phases from original design (this is phase 2 of 7)

**Codebase verified:** 2026-04-07

**Testing reference:** `/home/patrick/projects/road-trip/CLAUDE.md` (project testing conventions)

---

## Acceptance Criteria Coverage

This phase implements and tests:

### endpoint-registry.AC3: No hardcoded connections remain
- **endpoint-registry.AC3.1 Success:** road-trip Program.cs, PoiSeeder, and DesignTimeDbContextFactory all use `EndpointRegistry.Resolve()` (completing — Program.cs and DesignTimeDbContextFactory done in Phase 1)

### endpoint-registry.AC6: Environment selection is explicit and enforced
- **endpoint-registry.AC6.1 Success:** Seeder defaults to dev — running without flags never touches prod
- **endpoint-registry.AC6.2 Success:** Seeder `--environment prod` resolves from prod Key Vault (Note: actual Key Vault resolution requires Phase 3; this phase wires the flag and env var plumbing)
- **endpoint-registry.AC6.4 Failure:** Unrecognized environment name throws with list of valid environments

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Update PoiSeeder .csproj to include endpoints.json in output

**Files:**
- Modify: `/home/patrick/projects/road-trip/src/RoadTripMap.PoiSeeder/RoadTripMap.PoiSeeder.csproj`

**Implementation:**

The PoiSeeder already has a `<ProjectReference>` to `RoadTripMap.csproj` (line 4), so it has access to the `EndpointRegistry` class. However, it also needs `endpoints.json` copied to its own output directory.

Add an `<ItemGroup>` to copy `endpoints.json` from repo root:

```xml
<ItemGroup>
  <None Include="..\..\endpoints.json" CopyToOutputDirectory="PreserveNewest" Link="endpoints.json" />
</ItemGroup>
```

**Verification:**

Run: `dotnet build /home/patrick/projects/road-trip/src/RoadTripMap.PoiSeeder/RoadTripMap.PoiSeeder.csproj`
Expected: Build succeeds. Verify `endpoints.json` appears in PoiSeeder's `bin/Debug/net8.0/` output.

<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Wire PoiSeeder Program.cs to use EndpointRegistry with --environment flag

**Verifies:** endpoint-registry.AC3.1, endpoint-registry.AC6.1, endpoint-registry.AC6.2, endpoint-registry.AC6.4

**Files:**
- Modify: `/home/patrick/projects/road-trip/src/RoadTripMap.PoiSeeder/Program.cs`

**Implementation:**

The seeder's `Program.cs` needs four changes:

**Change 1: Add environment flag parsing (near top of Main method, after line ~15)**

Parse the new `--environment` argument. If provided, set `DOTNET_ENVIRONMENT` so the registry picks it up. Default to `"Development"` if not provided (maps to `dev` in the registry).

```csharp
// Parse --environment flag (defaults to dev)
var environmentArg = GetArgument(args, "--environment");
if (!string.IsNullOrEmpty(environmentArg))
{
    Environment.SetEnvironmentVariable("DOTNET_ENVIRONMENT", environmentArg switch
    {
        "dev" => "Development",
        "prod" => "Production",
        _ => environmentArg  // Let the registry throw for invalid values
    });
}
else
{
    // Ensure dev is the default for the seeder
    Environment.SetEnvironmentVariable("DOTNET_ENVIRONMENT",
        Environment.GetEnvironmentVariable("DOTNET_ENVIRONMENT") ?? "Development");
}
```

**Change 2: Replace connection string resolution (lines 22-23)**

Replace:
```csharp
var connectionString = Environment.GetEnvironmentVariable("WSL_SQL_CONNECTION")
    ?? "Server=localhost,1433;Database=RoadTrip;User Id=sa;Password=YourPassword123!;TrustServerCertificate=true;";
```

With:
```csharp
var connectionString = EndpointRegistry.Resolve("database");
```

**Change 3: Remove --confirm-remote safety check (lines 34-51)**

Remove the entire block that checks for remote database indicators (`.database.windows.net`, `tcp:`) and the `--confirm-remote` flag. The registry's environment selection replaces this safety mechanism — running without `--environment prod` will never resolve prod credentials.

Delete approximately lines 34-51 (the `if` block checking `connectionString.Contains(".database.windows.net")` and requiring `--confirm-remote`).

**Change 4: Replace NPS API key resolution (line 66)**

Replace:
```csharp
var npsApiKey = Environment.GetEnvironmentVariable("NPS_API_KEY") ?? string.Empty;
```

With:
```csharp
var npsApiKey = EndpointRegistry.Resolve("npsApi.apiKey");
```

Then update the NpsImporter instantiation to use this resolved key wherever it's passed.

**Verification:**

Run: `dotnet build /home/patrick/projects/road-trip/src/RoadTripMap.PoiSeeder/RoadTripMap.PoiSeeder.csproj`
Expected: Build succeeds with no errors.

<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Commit seeder wiring changes

**Step 1: Run all tests**

```bash
cd /home/patrick/projects/road-trip
dotnet test RoadTripMap.sln
```

Expected: All existing tests pass. No new tests needed for the seeder wiring itself — the EndpointRegistry tests from Phase 1 cover the resolver logic. The seeder is a console app that's tested operationally.

**Step 2: Verify seeder runs** (requires WSL_SQL_CONNECTION and NPS_API_KEY env vars set)

```bash
cd /home/patrick/projects/road-trip
dotnet run --project src/RoadTripMap.PoiSeeder -- --boundaries-only 2>&1 | head -5
```

Expected: Seeder starts and attempts to connect to dev database via registry. May fail if database is unavailable, but should NOT fail on env var resolution (confirming registry is working).

**Step 3: Verify --environment flag**

```bash
cd /home/patrick/projects/road-trip
dotnet run --project src/RoadTripMap.PoiSeeder -- --boundaries-only --environment bogus 2>&1 | head -5
```

Expected: Throws error about unknown environment (AC6.4 — unrecognized environment name with list of valid environments).

**Step 4: Commit**

```bash
cd /home/patrick/projects/road-trip
git add src/RoadTripMap.PoiSeeder/Program.cs src/RoadTripMap.PoiSeeder/RoadTripMap.PoiSeeder.csproj
git commit -m "feat: wire PoiSeeder through EndpointRegistry with --environment flag"
```

**Verification:**

Run: `git log -1 --stat`
Expected: Commit shows 2 files changed

<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->
