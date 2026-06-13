# Stack: Web App on Azure

<!-- Canonical source: claude-env/shared/claude-md/stack-web-azure.md. -->
<!-- Shared by stock-analyzer, road-trip, and (partially) photo-portfolio. -->
<!-- Project-specific resource names/keys belong in the repo's CLAUDE.local.md. -->

## Endpoint Registry
- All connection strings and API keys resolve through the endpoint registry (`EndpointRegistry.Resolve("name")`) backed by `endpoints.json`. NEVER read env vars directly for a known endpoint key, and never hardcode connection strings.
- Enforced by `endpoint_registry_guard.py` + `endpoint_schema_validator.py` (activate when `endpoints.json` exists at repo root).

## Azure Hygiene
- **Verify from the Azure source of truth** (App Service config / live resource state). Bicep files can be stale — don't trust them as current state.
- Infrastructure uses the shared Bicep modules published to ACR (e.g. `br:<registry>/bicep/modules/key-vault:<version>`) rather than inline resource blocks.
- Key Vault secret names and resource group names are project-specific — see CLAUDE.local.md. `azure_sp_identity_guard.py` blocks Azure CLI ops when the logged-in SP doesn't match `.claude/azure-identity.json`.
- Periodically clean up orphaned resources: stale SQL DBs, old container-registry tags, unused blobs.

## Deployment
- Deploy only on an explicit "deploy" + the repo's pre-deploy checklist. Deploys run through GitHub Actions (Azure preflight uses the shared `azure-deploy-preflight.yml`); no manual/CLI production deploys, and never click "Update branch" on the PR page.
- If the user is deploying, the previous PR is already merged — any follow-up fix is a NEW PR.

## Browser-Facing Changes
- Responsive testing before committing CSS: verify at mobile (390×844), tablet (768×1024), desktop (1400×900). Firefox is the primary browser — test there, and for any origin/CORS change include an OPTIONS preflight check plus a real browser check (curl does not enforce CORS).
