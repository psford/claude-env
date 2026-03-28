#!/usr/bin/env bash
set -euo pipefail

# Pull secrets from Azure Key Vault and generate .env file
# Usage: bash pull-secrets.sh [--vault-name NAME] [--output PATH]
#
# Requires: az login (run `az login` first if not authenticated)

VAULT_NAME=""
OUTPUT_PATH=""
PRIVATE_KEY_PATH="$HOME/.secrets/github-app-private-key.pem"

while [[ $# -gt 0 ]]; do
  case $1 in
    --vault-name) VAULT_NAME="$2"; shift 2 ;;
    --output) OUTPUT_PATH="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Auto-detect vault name if not provided
if [ -z "$VAULT_NAME" ]; then
  VAULT_NAME=$(az keyvault list --query "[0].name" -o tsv 2>/dev/null)
  if [ -z "$VAULT_NAME" ]; then
    echo "ERROR: No Key Vault found. Run 'az login' first, or pass --vault-name."
    exit 1
  fi
fi

# Auto-detect output path if not provided
if [ -z "$OUTPUT_PATH" ]; then
  # Look for repo root
  if [ -f "$HOME/projects/claude-env/.gitignore" ]; then
    OUTPUT_PATH="$HOME/projects/claude-env/.env"
  else
    OUTPUT_PATH="$(pwd)/.env"
  fi
fi

echo "Pulling secrets from Key Vault: $VAULT_NAME"
echo "Output: $OUTPUT_PATH"

# Function to pull a secret, returning empty string if not found
pull() {
  local name="$1"
  az keyvault secret show --vault-name "$VAULT_NAME" --name "$name" --query "value" -o tsv 2>/dev/null || echo ""
}

# Pull all secrets
echo "Pulling secrets..."
cat > "$OUTPUT_PATH" << ENVEOF
# Generated from Azure Key Vault ($VAULT_NAME)
# Generated at: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
# Re-generate: bash infrastructure/wsl/pull-secrets.sh

FINNHUB_API_KEY=$(pull FinnhubApiKey)
SLACK_BOT_TOKEN=$(pull SlackBotToken)
SLACK_APP_TOKEN=$(pull SlackAppToken)
JENKINS_USER=$(pull JenkinsUser)
JENKINS_PASSWORD=$(pull JenkinsPassword)
JENKINS_API_TOKEN=$(pull JenkinsApiToken)
CF_API_TOKEN=$(pull CfApiToken)
CF_ZONE_ID=$(pull CfZoneId)
TWELVEDATA_API_KEY=$(pull TwelvedataApiKey)
FMP_API_KEY=$(pull FmpApiKey)
MARKETAUX_API_TOKEN=$(pull MarketauxApiToken)
EODHD_API_KEY=$(pull EodhdApiKey)
CLOUDFLARE_API_TOKEN=$(pull CloudflareApiToken)
CLOUDFLARE_ZONE_ID=$(pull CloudflareZoneId)
PROD_SQL_CONNECTION=$(pull ProdSqlConnection)
GITHUB_APP_ID=$(pull GithubAppId)
GITHUB_APP_INSTALLATION_ID=$(pull GithubAppInstallationId)
GITHUB_APP_PRIVATE_KEY_PATH=$PRIVATE_KEY_PATH
ANTHROPIC_API_KEY=$(pull AnthropicApiKey)
ENVEOF

# The GithubAppPrivateKey secret contains the PEM file CONTENTS (not a path).
# The populate script (populate-keyvault.ps1) read the Windows-side .pem file
# and stored its contents as the secret value. Here we reverse the transformation:
# pull the contents from Key Vault and write them to a local file.
# The .env entry GITHUB_APP_PRIVATE_KEY_PATH points to this file path.
mkdir -p "$(dirname "$PRIVATE_KEY_PATH")"
PRIVATE_KEY_VALUE=$(pull GithubAppPrivateKey)
if [ -n "$PRIVATE_KEY_VALUE" ]; then
  echo "$PRIVATE_KEY_VALUE" > "$PRIVATE_KEY_PATH"
  chmod 600 "$PRIVATE_KEY_PATH"
  echo "Wrote GitHub App private key to $PRIVATE_KEY_PATH"
fi

# Pull WSL SQL passwords and set connection string env vars
# Two logins: wsl_claude (app, read/write) and wsl_claude_admin (migrations, db_owner)
WSL_SQL_PASSWORD=$(pull WslSqlPassword)
WSL_SQL_ADMIN_PASSWORD=$(pull WslSqlAdminPassword)
if [ -n "$WSL_SQL_PASSWORD" ]; then
  cat >> "$OUTPUT_PATH" << SQLEOF

# WSL2 SQL Express connection — APP login (db_datareader + db_datawriter)
# Used by the running app and most development operations
# Update DATABASE_NAME and credentials per your project
WSL_SQL_CONNECTION=Server=127.0.0.1,1433;Database=YourDatabase;User Id=wsl_claude;Password=$WSL_SQL_PASSWORD;TrustServerCertificate=True;

# WSL2 SQL Express connection — ADMIN login (db_owner, for EF migrations only)
# Used exclusively by dotnet ef database update
# Update DATABASE_NAME and credentials per your project
APP_DESIGN_CONNECTION=Server=127.0.0.1,1433;Database=YourDatabase;User Id=wsl_claude_admin;Password=${WSL_SQL_ADMIN_PASSWORD:-$WSL_SQL_PASSWORD};TrustServerCertificate=True;
SQLEOF
  echo "Added SQL connection strings to .env"
fi

chmod 600 "$OUTPUT_PATH"
echo ""
echo "Done. Secrets written to $OUTPUT_PATH"
echo "To add a new key: add to Key Vault, then re-run this script."
