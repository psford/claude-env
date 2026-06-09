// Reusable RBAC role-assignment module scoped to a Key Vault.
//
// Why a module: Bicep requires `roleAssignments[].scope` to be a typed
// resource reference (not a string), and that scope must match the
// current deployment's target resource group. When the Key Vault lives
// in a different RG (cross-RG access patterns), the only way to satisfy
// the scope rule is via a module targeting that RG. This module accepts
// the KV name and looks it up with `existing` inside.
//
// Generalizes the road-trip storage-rbac.bicep pattern for the most
// common target type (Key Vault) without needing a per-resource-type
// module library.
//
// Built-in role definition GUIDs for KV (most common):
//   Key Vault Administrator         00482a5a-887f-4fb3-b363-3b7fe8e74483
//   Key Vault Secrets Officer       b86a8fe4-44ce-4948-aee5-eccb2c155cd7
//   Key Vault Secrets User          4633458b-17de-408a-b874-0445c86b69e6
//   Key Vault Reader                21090545-7ca7-4776-b22c-e363652d74d2
// Full list: https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#key-vault
//
// Usage from a consumer main.bicep:
//
//   var kvSecretsUserId = '4633458b-17de-408a-b874-0445c86b69e6'
//
//   module funcKvAccess 'tools/claude-env/infrastructure/bicep/modules/key-vault-role-assignment.bicep' = {
//     name: 'funcKvAccess'
//     params: {
//       keyVaultName: kv.outputs.keyVaultName
//       principalId: functionApp.identity.principalId
//       roleDefinitionId: kvSecretsUserId
//     }
//   }
//
// The role-assignment resource name is auto-derived as a deterministic guid()
// so re-deploys are idempotent (no duplicate assignments).

@description('Name of the existing Key Vault to scope the role to.')
param keyVaultName string

@description('Principal (object) id to grant the role to.')
param principalId string

@description('Role definition GUID (just the GUID). See module-level comment for common KV roles.')
param roleDefinitionId string

@description('Principal type. Defaults to ServicePrincipal which covers managed identities, app registrations, and SPs.')
@allowed([ 'ServicePrincipal', 'User', 'Group' ])
param principalType string = 'ServicePrincipal'

resource keyVault 'Microsoft.KeyVault/vaults@2024-04-01-preview' existing = {
  name: keyVaultName
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, principalId, roleDefinitionId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
    principalId: principalId
    principalType: principalType
  }
}

@description('Role assignment resource id.')
output roleAssignmentId string = roleAssignment.id
