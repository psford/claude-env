// Reusable Key Vault module.
//
// Encapsulates the Key Vault provisioning pattern shared by stock-analyzer
// and road-trip:
//   - Standard SKU, family A
//   - RBAC authorization enabled (NOT access policies — RBAC is the
//     direction Microsoft is moving and what both companion projects
//     already use)
//   - Soft delete on (Azure default), retention parameterizable
//   - Tenant id auto-resolved from the current subscription
//
// Differences between consumers handled via parameters:
//   - Soft-delete retention days (stock-analyzer: 7; road-trip: 90 default)
//   - Purge protection (off by default; some workloads must turn it on)
//
// Usage from a consumer main.bicep:
//
//   module kv 'br/public:claude-env/key-vault:1.0.0' = {
//     name: 'kv'
//     params: {
//       keyVaultName: 'kv-stockanalyzer-prod'
//       location: location
//     }
//   }
//
// (Or via path until publishing to a Bicep registry:
//   module kv '../../../claude-env/infrastructure/bicep/modules/key-vault.bicep' = ...
// — bootstrap can symlink the path.)

@description('Key Vault resource name. Must be globally unique 3-24 chars [a-zA-Z0-9-].')
param keyVaultName string

@description('Azure region.')
param location string

@description('Soft-delete retention window in days. Range 7-90. Azure default is 90.')
@minValue(7)
@maxValue(90)
param softDeleteRetentionInDays int = 90

@description('Enable purge protection. Once on, cannot be turned off — soft-deleted vaults survive their retention window. Off by default; turn on for prod workloads where you accept the irreversibility.')
param enablePurgeProtection bool = false

@description('Tags applied to the vault.')
param tags object = {}

resource keyVault 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: softDeleteRetentionInDays
    enablePurgeProtection: enablePurgeProtection ? true : null
  }
}

@description('The created Key Vault resource id.')
output keyVaultId string = keyVault.id

@description('The created Key Vault name (echoed back for convenience).')
output keyVaultName string = keyVault.name

@description('The Key Vault DNS suffix consumers use in @Microsoft.KeyVault() app-settings references.')
output keyVaultUri string = keyVault.properties.vaultUri
