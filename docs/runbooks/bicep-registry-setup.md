# Bicep Modules: Publishing Pipeline Setup

One-time setup to give claude-env the ability to publish Bicep modules to the ACR registry. After this is done, releasing a new module version is just `git tag bicep/vX.Y.Z` + one approval click.

## Architecture

```
            (claude-env)
git tag bicep/v1.0.0
      │
      ▼
.github/workflows/publish-bicep-modules.yml
      │
      │  azure/login (OIDC, no long-lived secret)
      ▼
sp:github-claude-env-bicep  ──── AcrPush ────►  acrstockanalyzerer34ug.azurecr.io/bicep/modules/<name>:<ver>
                                                            ▲
                                                            │ (pull at deploy time)
                                                            │
                                  module kv 'br:acrstockanalyzerer34ug.azurecr.io/bicep/modules/key-vault:1.0.0'
                                                            (stock-analyzer, road-trip)
```

Key properties:
- **No long-lived secrets**: the publisher SP authenticates via OIDC federated credential.
- **Environment-gated**: each publish requires manual approval in the `bicep-publish` GitHub environment.
- **Tag-only**: only pushes to tags matching `bicep/v*` can run the publish workflow (the workflow trigger filters; the federated credential subject can be widened later if needed).
- **Single registry**: reuses the existing `acrstockanalyzerer34ug` ACR; no new infrastructure beyond the SP and federated credential.

## One-time setup

All commands assume you are signed in to the right Azure tenant (`az login` already done, `az account show --query name` is the right subscription).

### Step 1: Create the publisher SP and grant AcrPush

```bash
# Create the App Registration. This produces the appId we use as the client id.
APP_ID=$(az ad app create \
  --display-name github-claude-env-bicep \
  --query appId -o tsv)

# Create the SP for the app.
az ad sp create --id "$APP_ID" --query id -o tsv
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

# Get the ACR resource id (in rg-stockanalyzer-prod).
ACR_ID=$(az acr show \
  --name acrstockanalyzerer34ug \
  --query id -o tsv)

# Grant AcrPush on the registry only (least privilege — no broader RG access).
az role assignment create \
  --assignee "$SP_OBJECT_ID" \
  --role AcrPush \
  --scope "$ACR_ID"

echo ""
echo "=== Capture for the GitHub side ==="
echo "AZURE_BICEP_CLIENT_ID:       $APP_ID"
echo "AZURE_BICEP_TENANT_ID:       $(az account show --query tenantId -o tsv)"
echo "AZURE_BICEP_SUBSCRIPTION_ID: $(az account show --query id -o tsv)"
echo "SP_OBJECT_ID (for azure-identity.json): $SP_OBJECT_ID"
```

Copy the four IDs printed at the end — you'll need them for GitHub.

### Step 2: Create the federated identity credential

This is the magic step that lets GitHub Actions authenticate to Azure WITHOUT a secret.

```bash
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "github-claude-env-bicep-publish",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:psford/claude-env:environment:bicep-publish",
    "audiences": ["api://AzureADTokenExchange"],
    "description": "Allows the bicep-publish workflow in psford/claude-env to authenticate as github-claude-env-bicep when running in the bicep-publish GitHub environment."
  }'
```

The `subject` is the load-bearing part. It says: only a workflow run whose `environment: bicep-publish` matches this exact string is allowed to assume this identity. That ties the federated trust to the GitHub environment gate.

### Step 3: Update `.claude/azure-identity.json` in claude-env

The `azure_sp_identity_guard.py` hook reads this file and blocks `az` commands inside claude-env if the logged-in SP doesn't match. We declare the new publisher SP here so any local `az` operations are also gated.

Edit `.claude/azure-identity.json` and fill in the `SP_OBJECT_ID` you captured in Step 1 (the file in this PR has a placeholder).

```json
{
  "allowed_sp_object_ids": ["<paste SP_OBJECT_ID here>"],
  ...
}
```

Commit the update.

### Step 4: Create the GitHub environment

In the GitHub UI:

1. Navigate to `https://github.com/psford/claude-env/settings/environments`
2. Click **New environment**
3. Name: `bicep-publish`
4. Click **Configure environment**
5. Under **Deployment protection rules**:
   - Enable **Required reviewers**
   - Add yourself (`psford`)
6. (Optional but recommended) Under **Deployment branches and tags**:
   - Pick **Selected branches and tags**
   - Click **Add deployment branch or tag rule**
   - In the popover, **change the dropdown from "Ref type: Branch" to "Ref type: Tag"** (this is the load-bearing step — a Branch rule will NOT match a tag named `bicep/v1.0.0`)
   - Pattern: `bicep/v*`
   - Click **Add rule**
7. Save.

Or via `gh`:

```bash
# Get your user id (one-time)
USER_ID=$(gh api users/psford --jq .id)

# Create the environment
gh api -X PUT repos/psford/claude-env/environments/bicep-publish

# Add yourself as required reviewer (and enable custom branch/tag policies)
gh api -X PUT repos/psford/claude-env/environments/bicep-publish \
  --input - <<EOF
{
  "reviewers": [{"type": "User", "id": $USER_ID}],
  "deployment_branch_policy": {
    "protected_branches": false,
    "custom_branch_policies": true
  }
}
EOF

# Add the tag policy (type MUST be "tag", not "branch" — a branch policy
# named bicep/v* will not match a tag named bicep/v1.0.0 and will silently
# reject the deployment)
gh api -X POST repos/psford/claude-env/environments/bicep-publish/deployment-branch-policies \
  --input - <<'EOF'
{
  "name": "bicep/v*",
  "type": "tag"
}
EOF
```

### Step 5: Add the three GitHub repository variables

These are **variables**, not secrets — they're not sensitive (the SP can only assume the federated identity from the exact subject claim).

Via UI:

1. Navigate to `https://github.com/psford/claude-env/settings/variables/actions` — this is the **repository** Settings → Secrets and variables → Actions → Variables page (NOT your personal-account settings; "Secrets and variables" only appears in the sidebar when you're inside a repo's Settings tab).
2. Click **New repository variable** for each of the three. Set the values from Step 1's output:
   - `AZURE_BICEP_CLIENT_ID` = the `APP_ID`
   - `AZURE_BICEP_TENANT_ID` = the `tenantId`
   - `AZURE_BICEP_SUBSCRIPTION_ID` = the subscription id

Or via `gh`:

```bash
gh variable set AZURE_BICEP_CLIENT_ID       --body "$APP_ID"        --repo psford/claude-env
gh variable set AZURE_BICEP_TENANT_ID       --body "$TENANT_ID"     --repo psford/claude-env
gh variable set AZURE_BICEP_SUBSCRIPTION_ID --body "$SUBSCRIPTION"  --repo psford/claude-env
```

### Step 6: Smoke test

Cut the first tag and watch the workflow run.

```bash
cd /path/to/claude-env
git checkout main
git pull
git tag bicep/v1.0.0
git push origin bicep/v1.0.0
```

In GitHub Actions:
1. The `Publish Bicep Modules` workflow run will be pending on the `bicep-publish` environment approval.
2. Approve it.
3. After completion, verify the modules are in the ACR:
   ```bash
   az acr repository list --name acrstockanalyzerer34ug --output tsv | grep '^bicep/'
   az acr repository show-tags --name acrstockanalyzerer34ug --repository bicep/modules/key-vault --output tsv
   ```

You should see `1.0.0` listed.

## Releasing subsequent versions

After the initial setup, releasing a new module version is:

1. Make module changes in a feature branch, PR, merge to main.
2. From local main: `git tag bicep/vX.Y.Z && git push origin bicep/vX.Y.Z`
3. Approve the workflow run in the `bicep-publish` environment.

That's it. No further Azure work; the federated credential is reused.

## Versioning policy

For now, **all modules version together** under a single tag. `bicep/v1.0.0` publishes every module in `infrastructure/bicep/modules/` at version `1.0.0`. Pros: simpler mental model; consumers can pin one version. Cons: bumping a single module forces an unchanged-module re-publish at the same version.

When the module library grows enough that this gets painful, we'll split into per-module tags (`bicep/key-vault/v1.0.1`). Until then, keep it simple.

## Consumer usage

Once a version is published, consumers reference modules via the registry path:

```bicep
module kv 'br:acrstockanalyzerer34ug.azurecr.io/bicep/modules/key-vault:1.0.0' = {
  name: 'kv'
  params: {
    keyVaultName: 'kv-myproject-prod'
    location: location
  }
}
```

The deploying SP needs `AcrPull` on the registry. Stock-analyzer's `github-stockanalyzer` and road-trip's `github-deploy-rt` both already have AcrPush (which includes pull) on this ACR, so no additional role assignment is needed for those consumers. New consumers need `AcrPull` granted explicitly.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Workflow run pending forever | Required reviewer not added or no email/notification | Manually approve in Actions → workflow run → Review deployments |
| `az login` step fails with `AADSTS70021` or `subject_claim` mismatch | The federated credential `subject` doesn't match the workflow's environment | Verify the federated credential subject is exactly `repo:psford/claude-env:environment:bicep-publish` |
| `az acr login` fails with `Unauthorized` | SP missing AcrPush role | Re-run Step 1's `az role assignment create` |
| `az bicep publish` errors with `Repository not found` | First-time publish; ACR auto-creates the repo on first push | Verify ACR `Standard` SKU or higher (basic is fine too); re-run; if it persists, manually `az acr repository update` |
| Variables `AZURE_BICEP_*` not picked up | Set as Secrets instead of Variables | Re-add under Repository Variables; `vars.X` reads variables, `secrets.X` reads secrets |
| Workflow fails immediately with `Tag "bicep/vX.Y.Z" is not allowed to deploy to bicep-publish due to environment protection rules` | The environment's deployment policy was added as type `branch` instead of `tag`. The UI's "Add deployment branch or tag rule" defaults to Branch. | Delete the existing policy and create one with type `tag`: `gh api -X POST repos/psford/claude-env/environments/bicep-publish/deployment-branch-policies --input - <<<'{"name":"bicep/v*","type":"tag"}'`. Verify with `gh api repos/.../deployment-branch-policies` — `type` must read `tag`. Then `Re-run jobs` on the failed workflow (no need to re-tag). |

## Rotating credentials

OIDC has no long-lived secret to rotate, which is the whole point. The only credentials this design produces are:
- The SP itself: rotated by deleting + recreating the App Registration if compromised
- The federated credential: can be deleted (`az ad app federated-credential delete`) and re-created with a new subject

If the SP needs to be revoked entirely:
```bash
az role assignment delete --assignee "$SP_OBJECT_ID" --scope "$ACR_ID"
az ad app delete --id "$APP_ID"
```

After deletion, update `.claude/azure-identity.json` to remove the SP from `allowed_sp_object_ids`.

## Why this design

- **OIDC, not SP secret**: long-lived secrets are the #1 source of CI credential incidents. OIDC eliminates them entirely. The cost is one extra federated-credential setup step.
- **Environment-gated, not tag-only**: a stolen GitHub token with write access to claude-env can push a tag. The environment gate adds a manual approval that requires the holder to also have human GitHub access as you.
- **Existing ACR, not new one**: a separate registry for shared modules would be cleaner conceptually but adds Azure resources (cost, IAM surface) for no clear gain. The existing ACR is already trusted by all consumers.
- **AcrPush on registry, not on RG**: scope the role assignment as narrowly as possible. The SP can push to ONE resource and nothing else.

## What this runbook does NOT cover

- Module *authoring* (use `az bicep build` to compile locally; see `infrastructure/bicep/modules/README.md`)
- Consumer migration (per-repo PRs that swap inline KV resources for `br:` module references — separate PRs in each consuming repo)
- Multi-region failover for the ACR (not needed at current scale)
