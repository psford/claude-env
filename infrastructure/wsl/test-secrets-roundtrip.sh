#!/usr/bin/env bash
# test-secrets-roundtrip.sh — Validates Key Vault <-> .env consistency
# Mitigation #10: ensure all expected secrets exist in both locations.
set -euo pipefail

# ---------------------------------------------------------------------------
# Color output with fallback
# ---------------------------------------------------------------------------
if [[ -t 1 ]] && command -v tput &>/dev/null && [[ $(tput colors 2>/dev/null || echo 0) -ge 8 ]]; then
    GREEN=$(tput setaf 2)
    RED=$(tput setaf 1)
    YELLOW=$(tput setaf 3)
    RESET=$(tput sgr0)
else
    GREEN=""
    RED=""
    YELLOW=""
    RESET=""
fi

pass()  { echo "  ${GREEN}[PASS]${RESET} $1"; }
fail()  { echo "  ${RED}[FAIL]${RESET} $1"; }
warn()  { echo "  ${YELLOW}[WARN]${RESET} $1"; }

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
kv_total=0
kv_ok=0
env_total=0
env_ok=0
errors=0

# ---------------------------------------------------------------------------
# 1. Azure CLI authentication check
# ---------------------------------------------------------------------------
echo "Checking Azure CLI authentication..."
if ! az account show &>/dev/null; then
    echo "${RED}ERROR:${RESET} Azure CLI is not authenticated. Run 'az login' first."
    exit 1
fi
pass "Azure CLI authenticated"
echo ""

# ---------------------------------------------------------------------------
# 2. Auto-detect vault name
# ---------------------------------------------------------------------------
echo "Detecting Key Vault..."
VAULT_NAME=$(az keyvault list --query "[0].name" -o tsv 2>/dev/null || true)
if [[ -z "$VAULT_NAME" ]]; then
    echo "${RED}ERROR:${RESET} No Key Vault found in the current subscription."
    exit 1
fi
pass "Using vault: $VAULT_NAME"
echo ""

# ---------------------------------------------------------------------------
# 3. Expected Key Vault secret names
# ---------------------------------------------------------------------------
KV_SECRETS=(
    FinnhubApiKey
    SlackBotToken
    SlackAppToken
    JenkinsUser
    JenkinsPassword
    JenkinsApiToken
    CfApiToken
    CfZoneId
    TwelvedataApiKey
    FmpApiKey
    MarketauxApiToken
    EodhdApiKey
    CloudflareApiToken
    CloudflareZoneId
    ProdSqlConnection
    GithubAppId
    GithubAppInstallationId
    GithubAppPrivateKey
    AnthropicApiKey
    WslSqlPassword
    WslSqlAdminPassword
)

echo "Checking Key Vault secrets (${#KV_SECRETS[@]} expected)..."
for secret in "${KV_SECRETS[@]}"; do
    kv_total=$((kv_total + 1))
    value=$(az keyvault secret show --vault-name "$VAULT_NAME" --name "$secret" --query "value" -o tsv 2>/dev/null || true)
    if [[ -n "$value" ]]; then
        pass "$secret"
        kv_ok=$((kv_ok + 1))
    else
        fail "$secret — missing or empty"
        errors=$((errors + 1))
    fi
done
echo ""

# ---------------------------------------------------------------------------
# 4. Expected .env keys
# ---------------------------------------------------------------------------
ENV_FILE="$HOME/projects/claudeProjects/.env"

ENV_KEYS=(
    FINNHUB_API_KEY
    SLACK_BOT_TOKEN
    SLACK_APP_TOKEN
    EODHD_API_KEY
    ANTHROPIC_API_KEY
    WSL_SQL_CONNECTION
    SA_DESIGN_CONNECTION
    RT_DESIGN_CONNECTION
    GITHUB_APP_PRIVATE_KEY_PATH
)

echo "Checking .env file: $ENV_FILE"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "${RED}ERROR:${RESET} .env file not found at $ENV_FILE"
    errors=$((errors + ${#ENV_KEYS[@]}))
    env_total=${#ENV_KEYS[@]}
else
    for key in "${ENV_KEYS[@]}"; do
        env_total=$((env_total + 1))
        # Extract value: match KEY=VALUE, strip optional quotes
        value=$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | head -1 | sed "s/^${key}=//" | sed 's/^["'"'"']//;s/["'"'"']$//' || true)
        if [[ -n "$value" ]]; then
            pass "$key"
            env_ok=$((env_ok + 1))
        else
            fail "$key — missing or empty"
            errors=$((errors + 1))
        fi
    done
fi
echo ""

# ---------------------------------------------------------------------------
# 5. GitHub App private key file exists
# ---------------------------------------------------------------------------
echo "Checking GitHub App private key file..."
gh_key_path=$(grep -E "^GITHUB_APP_PRIVATE_KEY_PATH=" "$ENV_FILE" 2>/dev/null | head -1 | sed 's/^GITHUB_APP_PRIVATE_KEY_PATH=//' | sed 's/^["'"'"']//;s/["'"'"']$//' || true)
if [[ -z "$gh_key_path" ]]; then
    fail "GITHUB_APP_PRIVATE_KEY_PATH not set in .env — cannot verify key file"
    errors=$((errors + 1))
elif [[ -f "$gh_key_path" ]]; then
    pass "Private key file exists: $gh_key_path"
else
    fail "Private key file NOT found: $gh_key_path"
    errors=$((errors + 1))
fi
echo ""

# ---------------------------------------------------------------------------
# 6. WSL SQL passwords (already checked above, but call out explicitly)
# ---------------------------------------------------------------------------
echo "Checking WSL SQL passwords in Key Vault..."
for secret in WslSqlPassword WslSqlAdminPassword; do
    value=$(az keyvault secret show --vault-name "$VAULT_NAME" --name "$secret" --query "value" -o tsv 2>/dev/null || true)
    if [[ -n "$value" ]]; then
        pass "$secret is set"
    else
        warn "$secret — already counted above"
    fi
done
echo ""

# ---------------------------------------------------------------------------
# 7. Summary
# ---------------------------------------------------------------------------
echo "=============================="
echo "  SUMMARY"
echo "=============================="
echo "  Key Vault secrets: ${kv_ok}/${kv_total} present"
echo "  .env keys:         ${env_ok}/${env_total} present"
echo ""

if [[ $errors -eq 0 ]]; then
    echo "${GREEN}All checks passed.${RESET}"
    exit 0
else
    echo "${RED}${errors} issue(s) found.${RESET}"
    exit 1
fi
