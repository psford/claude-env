# Endpoint Registry Implementation Plan

**Goal:** Migrate remaining stock-analyzer API keys (TwelveData, FMP, Marketaux) and the database connection string to Key Vault, replacing inline Bicep credentials with `@Microsoft.KeyVault()` references.

**Architecture:** Stock-analyzer's Key Vault (`kv-stk-XXXXXX`, dynamically named) already has FinnhubApiKey and EodhdApiKey. This phase adds TwelveDataApiKey, FmpApiKey, MarketauxApiToken, and DbConnectionString as new secrets. App settings switch from inline parameters to Key Vault references. The managed identity role assignment already exists.

**Tech Stack:** Bicep, Azure Key Vault, GitHub Actions secrets

**Scope:** 7 phases from original design (this is phase 5 of 7)

**Codebase verified:** 2026-04-07

---

## Acceptance Criteria Coverage

This phase implements:

### endpoint-registry.AC4: All prod secrets in Key Vault
- **endpoint-registry.AC4.2 Success:** stock-analyzer Key Vault contains all 5 API keys + DbConnectionString
- **endpoint-registry.AC4.3 Success:** Bicep references all secrets via `@Microsoft.KeyVault(...)` — no plaintext

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Add new Key Vault secrets and Bicep parameters

**Verifies:** endpoint-registry.AC4.2

**Files:**
- Modify: `/home/patrick/projects/stock-analyzer/infrastructure/azure/main.bicep`

**Implementation:**

The existing Bicep already has Key Vault resource (lines 126-169) with FinnhubApiKey and EodhdApiKey secrets plus the managed identity role assignment.

**Add 3 new `@secure()` parameters** (after existing eodhdApiKey param, around line 23):

```bicep
@description('TwelveData API key')
@secure()
param twelveDataApiKey string

@description('FMP API key')
@secure()
param fmpApiKey string

@description('Marketaux API token')
@secure()
param marketauxApiToken string
```

**Add 4 new Key Vault secret resources** (after existing eodhdSecret resource, around line 157):

```bicep
resource twelveDataSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'TwelveDataApiKey'
  properties: { value: twelveDataApiKey }
}

resource fmpSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'FmpApiKey'
  properties: { value: fmpApiKey }
}

resource marketauxSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'MarketauxApiToken'
  properties: { value: marketauxApiToken }
}

resource dbConnectionSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'DbConnectionString'
  properties: {
    value: 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},1433;Database=${sqlDatabaseName};User ID=${sqlAdminUsername};Password=${sqlAdminPassword};Encrypt=true;TrustServerCertificate=false;Connection Timeout=30;Min Pool Size=2;'
  }
}
```

**Verification:**

Run: `az bicep build --file /home/patrick/projects/stock-analyzer/infrastructure/azure/main.bicep`
Expected: Builds without errors.

<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Switch app settings to Key Vault references

**Verifies:** endpoint-registry.AC4.3

**Files:**
- Modify: `/home/patrick/projects/stock-analyzer/infrastructure/azure/main.bicep` (app settings section)

**Implementation:**

Update the App Service `appSettings` section to use `@Microsoft.KeyVault()` references instead of inline values.

**Existing Key Vault references to keep** (already correct):
```bicep
{ name: 'Finnhub__ApiKey', value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=FinnhubApiKey)' }
{ name: 'Eodhd__ApiKey', value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=EodhdApiKey)' }
```

**Add new Key Vault references:**
```bicep
{ name: 'StockDataProviders__TwelveData__ApiKey', value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=TwelveDataApiKey)' }
{ name: 'StockDataProviders__FMP__ApiKey', value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=FmpApiKey)' }
{ name: 'Marketaux__ApiToken', value: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=MarketauxApiToken)' }
```

**Replace inline connection string** (lines 85-91) with Key Vault reference:

```bicep
// BEFORE:
connectionStrings: [
  {
    name: 'DefaultConnection'
    connectionString: 'Server=tcp:${sqlServer.properties.fullyQualifiedDomainName},...'
    type: 'SQLAzure'
  }
]

// AFTER:
connectionStrings: [
  {
    name: 'DefaultConnection'
    connectionString: '@Microsoft.KeyVault(VaultName=${keyVault.name};SecretName=DbConnectionString)'
    type: 'SQLAzure'
  }
]
```

**Verification:**

Run: `az bicep build --file /home/patrick/projects/stock-analyzer/infrastructure/azure/main.bicep`
Expected: Builds without errors.

<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Verify endpoints.json prod section matches and commit

**Files:**
- Read: `/home/patrick/projects/stock-analyzer/endpoints.json` (verify vault/secret names match Bicep)
- Stage: `/home/patrick/projects/stock-analyzer/infrastructure/azure/main.bicep`

**Implementation:**

Verify the `prod` section of `endpoints.json` (created in Phase 4) matches the Key Vault and secret names from the updated Bicep. The Key Vault name in endpoints.json must match the Bicep variable pattern.

**Note:** The Key Vault name is dynamically generated (`kv-stk-${shortSuffix}`) which means the exact vault name isn't known at commit time. The endpoints.json `vault` field should be set to the actual deployed vault name. Query the current vault name if accessible:

```bash
az keyvault list --resource-group <rg-name> --query "[?starts_with(name, 'kv-stk-')].name" -o tsv
```

Update endpoints.json `prod` entries if the vault name doesn't match.

**Verify managed identity role assignment (AC4.4):**

Confirm the App Service managed identity has `Key Vault Secrets User` role on the Key Vault. This should already exist from the existing Bicep (lines 160-168), but verify:

```bash
# Get the Key Vault resource ID
KV_ID=$(az keyvault show --name <actual-vault-name> --query id -o tsv)
# Check role assignment
az role assignment list --scope "$KV_ID" --query "[?roleDefinitionName=='Key Vault Secrets User']" -o table
```

Expected: At least one assignment for the App Service managed identity principal. If missing, the Bicep already declares it — a fresh deployment will create it.

**Commit:**

```bash
cd /home/patrick/projects/stock-analyzer
git add infrastructure/azure/main.bicep endpoints.json
git commit -m "feat: migrate all API keys and DB connection to Key Vault references"
```

**Verification:**

Run: `git log -1 --stat`
Expected: Commit shows Bicep changes and possibly endpoints.json update.

<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->
