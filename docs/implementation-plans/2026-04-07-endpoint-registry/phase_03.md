# Endpoint Registry Implementation Plan

**Goal:** Create road-trip Key Vault in Bicep, store all prod secrets there, switch app settings to `@Microsoft.KeyVault()` references, and implement the `keyvault` source type in EndpointRegistry.

**Architecture:** Key Vault is provisioned via Bicep alongside existing resources. App Service's system-assigned managed identity gets `Key Vault Secrets User` role. Bicep app settings use `@Microsoft.KeyVault(VaultName=...;SecretName=...)` syntax so Azure injects secrets at deploy time. The C# `EndpointRegistry` resolver also gains direct Key Vault resolution via `Azure.Security.KeyVault.Secrets` for scenarios where the app resolves at runtime (e.g., seeder running locally with `--environment prod`).

**Tech Stack:** Bicep, Azure Key Vault, Azure.Security.KeyVault.Secrets, Azure.Identity, C# / .NET 8.0

**Scope:** 7 phases from original design (this is phase 3 of 7)

**Codebase verified:** 2026-04-07

**Testing reference:** `/home/patrick/projects/road-trip/CLAUDE.md` (project testing conventions)

---

## Acceptance Criteria Coverage

This phase implements and tests:

### endpoint-registry.AC2: Resolver provides the only path to endpoints
- **endpoint-registry.AC2.4 Success:** `keyvault` sources fetch from Azure Key Vault
- **endpoint-registry.AC2.6 Failure:** Missing Key Vault secret throws descriptive error naming the vault and secret

### endpoint-registry.AC4: All prod secrets in Key Vault
- **endpoint-registry.AC4.1 Success:** road-trip Key Vault contains DbConnectionString, BlobStorageConnection, NpsApiKey
- **endpoint-registry.AC4.3 Success:** Bicep references all secrets via `@Microsoft.KeyVault(...)` — no plaintext
- **endpoint-registry.AC4.4 Success:** App Service managed identities have Key Vault Secrets User role

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Add Key Vault resource and secrets to Bicep

**Verifies:** endpoint-registry.AC4.1, endpoint-registry.AC4.3, endpoint-registry.AC4.4

**Files:**
- Modify: `/home/patrick/projects/road-trip/infrastructure/azure/main.bicep` (add Key Vault resource, secrets, role assignment, update app settings)
- Modify: `/home/patrick/projects/road-trip/infrastructure/azure/parameters.json` (add NPS API key parameter)

**Implementation:**

The current `main.bicep` has these resources (in order): SQL Server (line 16), SQL Database (line 28), SQL Firewall Rule (line 44), App Service Plan (line 54), App Service (line 74). The SQL connection string is hardcoded inline at line 71 with plain-text password. App settings at lines 87-108 pass connection strings directly.

Add the following after the App Service Plan resource (after line 68) and before the App Service resource (line 74):

**Key Vault resource:**
- Name: `kv-roadtripmap-prod` (matches design's endpoints.json)
- SKU: standard
- Enable RBAC authorization (no access policies — use role assignments instead)
- Tenant ID from subscription

**Key Vault secrets (3):**
- `DbConnectionString` — constructed from SQL Server FQDN, database name, admin credentials (same connection string currently at line 71, but now stored as a secret)
- `BlobStorageConnection` — from the `storageConnectionString` parameter
- `NpsApiKey` — from a new `npsApiKey` parameter (add `@secure()`)

**Role assignment:**
- Assign `Key Vault Secrets User` role (role ID: `4633458b-17de-408a-b874-0445c86b69e6`) to the App Service's system-assigned managed identity (`appService.identity.principalId`)
- Scope to the Key Vault resource

**Update App Service app settings (lines 87-108):**

Replace the hardcoded connection strings:

```bicep
// BEFORE:
ConnectionStrings__DefaultConnection: sqlConnectionString  // plain-text variable

// AFTER:
ConnectionStrings__DefaultConnection: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=DbConnectionString)'
```

```bicep
// BEFORE:
ConnectionStrings__AzureStorage: storageConnectionString  // parameter

// AFTER:
ConnectionStrings__AzureStorage: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=BlobStorageConnection)'
```

Add NPS API key app setting:
```bicep
NPS_API_KEY: '@Microsoft.KeyVault(VaultName=${keyVaultName};SecretName=NpsApiKey)'
```

**Remove** the inline `sqlConnectionString` variable (line 71) — it's now constructed inside the Key Vault secret.

**Add parameters to `parameters.json`:**
- `npsApiKey`: `"#{NpsApiKey}#"` (tokenized for CI/CD replacement, same pattern as `sqlAdminPassword`)

**Verification:**

Validate Bicep syntax:
```bash
cd /home/patrick/projects/road-trip
az bicep build --file infrastructure/azure/main.bicep
```

Expected: Builds without errors (validates syntax, not deployment).

<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Commit Bicep changes

**Step 1: Stage and commit**

```bash
cd /home/patrick/projects/road-trip
git add infrastructure/azure/main.bicep infrastructure/azure/parameters.json
git commit -m "feat: add Key Vault resource, migrate secrets to @Microsoft.KeyVault references"
```

**Verification:**

Run: `git log -1 --stat`
Expected: 2 files changed

<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Verify endpoints.json prod section matches Key Vault names

**Files:**
- Read: `/home/patrick/projects/road-trip/endpoints.json` (verify, may need minor updates)

**Implementation:**

Verify the `prod` section of `endpoints.json` (created in Phase 1) matches the Key Vault and secret names from the Bicep:

- `database.vault` = `kv-roadtripmap-prod`, `database.secret` = `DbConnectionString`
- `blobStorage.vault` = `kv-roadtripmap-prod`, `blobStorage.secret` = `BlobStorageConnection`
- `npsApi.apiKey.vault` = `kv-roadtripmap-prod`, `npsApi.apiKey.secret` = `NpsApiKey`

If any names don't match between endpoints.json and Bicep, update endpoints.json to be consistent.

**Verification:**

Visual comparison of vault/secret names between `main.bicep` and `endpoints.json`.

<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->

<!-- START_SUBCOMPONENT_B (tasks 4-6) -->

<!-- START_TASK_4 -->
### Task 4: Add Azure Key Vault NuGet packages and implement keyvault source resolution

**Verifies:** endpoint-registry.AC2.4, endpoint-registry.AC2.6

**Files:**
- Modify: `/home/patrick/projects/road-trip/src/RoadTripMap/RoadTripMap.csproj` (add NuGet packages)
- Modify: `/home/patrick/projects/road-trip/src/RoadTripMap/EndpointRegistry.cs` (implement keyvault resolution)

**Implementation:**

Add NuGet packages to `RoadTripMap.csproj`:

```xml
<PackageReference Include="Azure.Security.KeyVault.Secrets" Version="4.6.0" />
<PackageReference Include="Azure.Identity" Version="1.13.2" />
```

In `EndpointRegistry.cs`, replace the `keyvault` case in `ResolveEntry()`:

```csharp
// BEFORE:
"keyvault" => throw new NotImplementedException(
    $"Key Vault resolution not yet implemented (endpoint '{name}'). See Phase 3."),

// AFTER:
"keyvault" => ResolveKeyVault(entry, name),
```

Add the `ResolveKeyVault` method:

```csharp
private static string ResolveKeyVault(JsonElement entry, string name)
{
    var vaultName = entry.GetProperty("vault").GetString()!;
    var secretName = entry.GetProperty("secret").GetString()!;

    try
    {
        var client = new Azure.Security.KeyVault.Secrets.SecretClient(
            new Uri($"https://{vaultName}.vault.azure.net"),
            new Azure.Identity.DefaultAzureCredential());

        var secret = client.GetSecret(secretName);
        return secret.Value.Value;
    }
    catch (Azure.RequestFailedException ex) when (ex.Status == 404)
    {
        throw new InvalidOperationException(
            $"Key Vault secret '{secretName}' not found in vault '{vaultName}' for endpoint '{name}'",
            ex);
    }
    catch (Azure.Identity.AuthenticationFailedException ex)
    {
        throw new InvalidOperationException(
            $"Failed to authenticate to Key Vault '{vaultName}' for endpoint '{name}'. " +
            "Ensure managed identity or local credentials are configured.",
            ex);
    }
}
```

Add the required `using` statements at the top of the file (if not already present — the fully-qualified names in the method body avoid needing top-level usings, but add them for clarity if preferred).

**Note:** `SecretClient.GetSecret()` is the synchronous overload. This is appropriate because `Resolve()` is called at startup (via `ValidateAll()`) and during one-time seeder runs, not in hot request paths.

**Verification:**

Run: `dotnet build /home/patrick/projects/road-trip/src/RoadTripMap/RoadTripMap.csproj`
Expected: Build succeeds with no errors.

<!-- END_TASK_4 -->

<!-- START_TASK_5 -->
### Task 5: Update EndpointRegistry tests for keyvault source type

**Verifies:** endpoint-registry.AC2.4, endpoint-registry.AC2.6

**Files:**
- Modify: `/home/patrick/projects/road-trip/tests/RoadTripMap.Tests/EndpointRegistryTests.cs`

**Testing:**

Tests for Key Vault resolution cannot actually call Azure Key Vault in unit tests. Test the error paths that don't require live credentials:

- **endpoint-registry.AC2.6:** When keyvault source is configured but vault is unreachable (authentication fails), the error message includes the vault name and secret name
- **keyvault entry parsing:** Verify that a keyvault entry in test-endpoints.json is recognized as source type "keyvault" and attempts resolution (catches the expected AuthenticationFailedException and verifies the error message format)

The test fixture (`test-endpoints.json`) should include a `prod` environment with a keyvault entry pointing to a non-existent vault. The test verifies the error message format.

Note: Full integration testing of Key Vault resolution requires a live vault and credentials, which is covered by the deploy pipeline smoke tests (Phase 7), not unit tests.

**Verification:**

Run: `dotnet test /home/patrick/projects/road-trip/tests/RoadTripMap.Tests/ --filter "FullyQualifiedName~EndpointRegistry"`
Expected: All EndpointRegistry tests pass

<!-- END_TASK_5 -->

<!-- START_TASK_6 -->
### Task 6: Run all tests and commit

**Step 1: Run all tests**

```bash
cd /home/patrick/projects/road-trip
dotnet test RoadTripMap.sln
```

Expected: All tests pass.

**Step 2: Commit**

```bash
cd /home/patrick/projects/road-trip
git add src/RoadTripMap/EndpointRegistry.cs src/RoadTripMap/RoadTripMap.csproj tests/RoadTripMap.Tests/EndpointRegistryTests.cs tests/RoadTripMap.Tests/Fixtures/test-endpoints.json
git commit -m "feat: implement Key Vault source resolution in EndpointRegistry"
```

**Verification:**

Run: `git log -2 --oneline`
Expected: Two commits for Bicep changes and resolver implementation

<!-- END_TASK_6 -->

<!-- END_SUBCOMPONENT_B -->
