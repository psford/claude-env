# Stack: Web App on Azure

<!-- Canonical source: claude-env/shared/claude-md/stack-web-azure.md. -->
<!-- Shared by stock-analyzer, road-trip, and (partially) photo-portfolio. -->
<!-- Project-specific resource names/keys belong in the repo's CLAUDE.local.md. -->

A rule written as `specs/<file>.md#<section>` is held by that section of the spec corpus, in claude-harness's `plugins/psford-tickets/specs/`. Read the section before acting on the rule.

## Endpoint Registry
- **Connection strings and API keys:** `specs/api-design.md#endpoint-registry`

## Azure Hygiene
- **Live state over Bicep, the shared modules, and cleanup:** `specs/deployment.md#azure`
- **The logged-in service principal:** `specs/security.md#azure-identity`
- Key Vault secret names and resource group names are project-specific — see CLAUDE.local.md.

## Deployment
- **When and how to deploy:** `specs/deployment.md#deploy-gate`
- **A deploy means the previous PR is merged:** `specs/git.md#verify-git-and-pr-state`

## Browser-Facing Changes
- **Viewports, and Firefox first:** `specs/ui.md#firefox-first`
- **An origin or CORS change:** `specs/api-design.md#cors-checks`
