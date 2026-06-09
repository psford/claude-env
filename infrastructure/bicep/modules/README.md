# Bicep Modules

Reusable Bicep modules shared across companion projects that deploy to Azure (currently stock-analyzer, road-trip; future SysTTS/whisper-service if/when they grow Azure deployments).

## Available modules

### `key-vault.bicep`

Standard-SKU Key Vault with RBAC authorization, soft-delete on, purge protection optional.

**Parameters:**
- `keyVaultName` (required) — globally unique 3-24 char name
- `location` (required)
- `softDeleteRetentionInDays` (default 90, range 7-90)
- `enablePurgeProtection` (default false)
- `tags` (default `{}`)

**Outputs:** `keyVaultId`, `keyVaultName`, `keyVaultUri`.

### `key-vault-role-assignment.bicep`

RBAC role-assignment helper scoped to a Key Vault. Pairs with `key-vault.bicep` for cross-RG access patterns.

**Parameters:**
- `keyVaultName` (required) — name of the existing KV
- `principalId` (required)
- `roleDefinitionId` (required) — built-in role GUID; module comment lists the common ones
- `principalType` (default `ServicePrincipal`; also `User`, `Group`)

**Outputs:** `roleAssignmentId`.

Role-assignment name is auto-derived as `guid(keyVault.id, principalId, roleDefinitionId)` so re-deploys are idempotent (no duplicate assignments).

**Why not a generic role-assignment.bicep:** Bicep's `roleAssignments[].scope` requires a typed resource reference, not a string. Generic-by-string doesn't compile. Per-target-type modules (this file for KV) are the working pattern; add a `storage-role-assignment.bicep` etc. when a second target type starts to repeat in consumers.

## Usage pattern

Consumers reference modules via the Bicep registry at `acrstockanalyzerer34ug.azurecr.io`. Versions are pinned explicitly per `br:` reference.

```bicep
module kv 'br:acrstockanalyzerer34ug.azurecr.io/bicep/modules/key-vault:1.0.0' = {
  name: 'kv'
  params: {
    keyVaultName: 'kv-myproject-prod'
    location: location
    softDeleteRetentionInDays: 7
  }
}

var kvSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

module funcKvAccess 'br:acrstockanalyzerer34ug.azurecr.io/bicep/modules/key-vault-role-assignment:1.0.0' = {
  name: 'funcKvAccess'
  params: {
    keyVaultName: kv.outputs.keyVaultName
    principalId: functionApp.identity.principalId
    roleDefinitionId: kvSecretsUserRoleId
  }
}
```

The deploying SP needs `AcrPull` on the registry. Stock-analyzer's `github-stockanalyzer` and road-trip's `github-deploy-rt` both already have AcrPush (which includes pull) on this ACR, so no additional role assignment is needed for existing consumers. New consumers need `AcrPull` granted explicitly.

### Publishing new module versions

Modules are published by `.github/workflows/publish-bicep-modules.yml` on tag push (`bicep/vX.Y.Z`). The workflow requires manual approval in the `bicep-publish` GitHub environment.

See [docs/runbooks/bicep-registry-setup.md](../../../docs/runbooks/bicep-registry-setup.md) for the one-time SP + federated credential setup, and for the release procedure.

### Versioning

All modules version together under a single tag. `bicep/v1.0.0` publishes every `.bicep` file in this directory at version `1.0.0`. The consumer pins each module reference to a specific version. This keeps the mental model simple at the cost of forcing unchanged-module re-publishes — acceptable while the module library is small (currently 2 modules). When this gets painful, we'll split into per-module tags.

## What's intentionally NOT here

These resource types are common across companion projects but are NOT extracted into modules, by design:

- **App Service Plan + App Service** — each project's plan SKU, container vs zip deploy, app settings, identity choices, and connection string strategy differ enough that a parameterized module either gets bloated or forces all consumers into one shape. Leave inlined in consumer main.bicep until the variation surface narrows.
- **SQL Server + Database** — administrator login strategy (password vs Azure AD), firewall rules, backup retention all vary. Same rationale.
- **Function App / Static Web App** — workload-specific.

When a third consumer project adopts the same shape for one of these, extract a module then. Two consumers is not yet enough signal that the module parameter surface is stable.

## Adding a new module

1. Place the `.bicep` file in this directory.
2. Add a `tools[]` entry to `tooling-manifest.json` (the `manifest_completeness_guard.py` hook will block otherwise).
3. Document parameters + outputs + usage in this README.
4. If the module has a sibling test composition, place it under `tests/` and document how to deploy it to a sandbox subscription.

## Bicep build validation

Run `az bicep build --file modules/<name>.bicep` to confirm a module compiles without errors. Lint warnings (`BCP*`) should be addressed before commit; suppress only with explicit reasoning.

```bash
# From this directory:
for f in *.bicep; do
  az bicep build --file "$f" --stdout > /dev/null && echo "$f: OK"
done
```
