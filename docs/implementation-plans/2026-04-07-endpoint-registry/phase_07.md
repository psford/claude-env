# Endpoint Registry Implementation Plan

**Goal:** Add pre-deploy validation steps to both road-trip and stock-analyzer deploy workflows that confirm all Key Vault secrets referenced in `endpoints.json` exist before deploying.

**Architecture:** Each deploy workflow gets a new validation step in the preflight/pre-deploy job. The step reads `endpoints.json`, extracts all `keyvault` source entries for the prod environment, and uses `az keyvault secret show` to verify each secret exists. If any secret is missing, the workflow fails with a clear error message. Stock-analyzer's existing Bicep drift detection is extended to include endpoint registry validation.

**Tech Stack:** GitHub Actions, Azure CLI (`az keyvault secret show`), bash scripting

**Scope:** 7 phases from original design (this is phase 7 of 7)

**Codebase verified:** 2026-04-07

---

## Acceptance Criteria Coverage

This phase implements:

### endpoint-registry.AC5: Enforcement prevents regression
- **endpoint-registry.AC5.3 Success:** Deploy workflow validates all Key Vault secrets exist before deploying
- **endpoint-registry.AC5.4 Failure:** Deploy fails with clear error if referenced Key Vault secret doesn't exist

### endpoint-registry.AC6: Environment selection is explicit and enforced
- **endpoint-registry.AC6.3 Success:** Web app reads environment from ASPNETCORE_ENVIRONMENT

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Add Key Vault secret validation to road-trip deploy workflow

**Verifies:** endpoint-registry.AC5.3, endpoint-registry.AC5.4

**Files:**
- Modify: `/home/patrick/projects/road-trip/.github/workflows/deploy.yml`

**Implementation:**

The road-trip deploy workflow has a `preflight` job (lines 27-65) that validates credentials. Add a new step after Azure credential validation that reads `endpoints.json` and verifies all prod Key Vault secrets exist.

Add step after the Azure credential test step:

```yaml
- name: Validate endpoint registry Key Vault secrets
  run: |
    echo "::group::Validating endpoint registry secrets"
    
    # Parse endpoints.json for prod keyvault entries
    VAULT_SECRETS=$(python3 -c "
    import json, sys
    with open('endpoints.json') as f:
        data = json.load(f)
    prod = data.get('environments', {}).get('prod', {})
    for name, entry in prod.items():
        if isinstance(entry, dict):
            if entry.get('source') == 'keyvault':
                print(f\"{entry['vault']}|{entry['secret']}|{name}\")
            else:
                for sub_name, sub_entry in entry.items():
                    if isinstance(sub_entry, dict) and sub_entry.get('source') == 'keyvault':
                        print(f\"{sub_entry['vault']}|{sub_entry['secret']}|{name}.{sub_name}\")
    ")
    
    FAILED=0
    while IFS='|' read -r vault secret endpoint; do
      echo "Checking $vault/$secret (endpoint: $endpoint)..."
      if ! az keyvault secret show --vault-name "$vault" --name "$secret" --query "name" -o tsv > /dev/null 2>&1; then
        echo "::error::Key Vault secret '$secret' not found in vault '$vault' (endpoint: $endpoint)"
        FAILED=$((FAILED + 1))
      else
        echo "  ✓ $secret exists"
      fi
    done <<< "$VAULT_SECRETS"
    
    if [ "$FAILED" -gt 0 ]; then
      echo "::error::$FAILED Key Vault secret(s) missing. Deploy blocked."
      exit 1
    fi
    
    echo "All endpoint registry secrets verified."
    echo "::endgroup::"
```

**Verification:**

Validate YAML syntax:
```bash
python3 -c "import yaml; yaml.safe_load(open('/home/patrick/projects/road-trip/.github/workflows/deploy.yml'))"
```
Expected: No errors.

<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Add Key Vault secret validation to stock-analyzer deploy workflow

**Verifies:** endpoint-registry.AC5.3, endpoint-registry.AC5.4

**Files:**
- Modify: `/home/patrick/projects/stock-analyzer/.github/workflows/azure-deploy.yml`

**Implementation:**

The stock-analyzer deploy workflow has a `preflight` job (lines 32-110) with an existing Bicep drift detection step (lines 63-100). Add a new endpoint registry validation step after the drift detection step.

Add step after the "Verify Bicep matches live Azure config" step (after line 100):

```yaml
- name: Validate endpoint registry Key Vault secrets
  run: |
    echo "::group::Validating endpoint registry secrets"
    
    # Parse endpoints.json for prod keyvault entries
    VAULT_SECRETS=$(python3 -c "
    import json, sys
    with open('endpoints.json') as f:
        data = json.load(f)
    prod = data.get('environments', {}).get('prod', {})
    for name, entry in prod.items():
        if isinstance(entry, dict):
            if entry.get('source') == 'keyvault':
                print(f\"{entry['vault']}|{entry['secret']}|{name}\")
            else:
                for sub_name, sub_entry in entry.items():
                    if isinstance(sub_entry, dict) and sub_entry.get('source') == 'keyvault':
                        print(f\"{sub_entry['vault']}|{sub_entry['secret']}|{name}.{sub_name}\")
    ")
    
    FAILED=0
    while IFS='|' read -r vault secret endpoint; do
      echo "Checking $vault/$secret (endpoint: $endpoint)..."
      if ! az keyvault secret show --vault-name "$vault" --name "$secret" --query "name" -o tsv > /dev/null 2>&1; then
        echo "::error::Key Vault secret '$secret' not found in vault '$vault' (endpoint: $endpoint)"
        FAILED=$((FAILED + 1))
      else
        echo "  ✓ $secret exists"
      fi
    done <<< "$VAULT_SECRETS"
    
    if [ "$FAILED" -gt 0 ]; then
      echo "::error::$FAILED Key Vault secret(s) missing. Deploy blocked."
      exit 1
    fi
    
    echo "All endpoint registry secrets verified."
    echo "::endgroup::"
```

**Note:** The validation script is identical for both repos — it reads endpoints.json dynamically. For initial implementation, inline in each workflow is simplest. **Follow-up task:** Extract the validation script to `helpers/validate_keyvault_secrets.py` in claude-env and reference it from both workflows once the bootstrap script (Phase 6 of the broader claude-env plan) symlinks helpers into companion repos.

**Verification:**

Validate YAML syntax:
```bash
python3 -c "import yaml; yaml.safe_load(open('/home/patrick/projects/stock-analyzer/.github/workflows/azure-deploy.yml'))"
```
Expected: No errors.

<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Verify ASPNETCORE_ENVIRONMENT is set correctly and commit

**Verifies:** endpoint-registry.AC6.3

**Files:**
- Read: `/home/patrick/projects/road-trip/infrastructure/azure/main.bicep` (verify ASPNETCORE_ENVIRONMENT app setting)
- Read: `/home/patrick/projects/stock-analyzer/infrastructure/azure/main.bicep` (verify ASPNETCORE_ENVIRONMENT app setting)

**Implementation:**

Verify both Bicep templates set `ASPNETCORE_ENVIRONMENT` in app settings. This ensures the EndpointRegistry resolver picks up the correct environment in production.

**Road-trip (already confirmed):** Line ~94 has `ASPNETCORE_ENVIRONMENT: environment` parameter.

**Stock-analyzer (already confirmed):** Check that the `environment` parameter is passed to app settings.

If either is missing, add:
```bicep
{ name: 'ASPNETCORE_ENVIRONMENT', value: environment }
```

**Commit both repos:**

```bash
cd /home/patrick/projects/road-trip
git add .github/workflows/deploy.yml
git commit -m "feat: add Key Vault secret validation to deploy pipeline"

cd /home/patrick/projects/stock-analyzer
git add .github/workflows/azure-deploy.yml
git commit -m "feat: add Key Vault secret validation to deploy pipeline"
```

**Verification:**

Run in each repo: `git log -1 --stat`
Expected: Workflow file modified in each commit.

<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->
