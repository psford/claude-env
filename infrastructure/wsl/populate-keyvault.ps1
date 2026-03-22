# Populate Azure Key Vault with all API keys from .env
# Run from repo root on Windows: powershell -File infrastructure/wsl/populate-keyvault.ps1
#
# This is a ONE-TIME operation. After this, secrets are managed in Key Vault.
# pragma: allowlist secret

param(
    [string]$EnvFile = ".env",
    [string]$VaultName = ""
)

$az = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'

if (-not $VaultName) {
    $VaultName = & $az keyvault list --query "[0].name" -o tsv
    if (-not $VaultName) {
        Write-Error "No Key Vault found. Create one first."
        exit 1
    }
}
Write-Host "Using Key Vault: $VaultName"

# Mapping of .env variable names to Key Vault secret names
$secretMap = @{
    "FINNHUB_API_KEY"              = "FinnhubApiKey"
    "SLACK_BOT_TOKEN"              = "SlackBotToken"
    "SLACK_APP_TOKEN"              = "SlackAppToken"
    "JENKINS_USER"                 = "JenkinsUser"
    "JENKINS_PASSWORD"             = "JenkinsPassword"
    "JENKINS_API_TOKEN"            = "JenkinsApiToken"
    "CF_API_TOKEN"                 = "CfApiToken"
    "CF_ZONE_ID"                   = "CfZoneId"
    "TWELVEDATA_API_KEY"           = "TwelvedataApiKey"
    "FMP_API_KEY"                  = "FmpApiKey"
    "MARKETAUX_API_TOKEN"          = "MarketauxApiToken"
    "EODHD_API_KEY"                = "EodhdApiKey"
    "CLOUDFLARE_API_TOKEN"         = "CloudflareApiToken"
    "CLOUDFLARE_ZONE_ID"           = "CloudflareZoneId"
    "PROD_SQL_CONNECTION"          = "ProdSqlConnection"
    "GITHUB_APP_ID"                = "GithubAppId"
    "GITHUB_APP_INSTALLATION_ID"   = "GithubAppInstallationId"
    "GITHUB_APP_PRIVATE_KEY_PATH"  = "GithubAppPrivateKey"
    "ANTHROPIC_API_KEY"            = "AnthropicApiKey"
}

# Read .env file
$envContent = Get-Content $EnvFile | Where-Object { $_ -match '^\s*[A-Z]' }

foreach ($line in $envContent) {
    if ($line -match '^([A-Z_]+)\s*=\s*(.+)$') {
        $envName = $matches[1]
        $envValue = $matches[2].Trim('"', "'", ' ')

        if ($secretMap.ContainsKey($envName)) {
            $secretName = $secretMap[$envName]

            # Special case: GITHUB_APP_PRIVATE_KEY_PATH stores a FILE PATH on Windows
            # (e.g., C:\Users\patri\Documents\.secrets\...private-key.pem).
            # We read the file's CONTENTS and store them as the secret value.
            # The pull script (pull-secrets.sh) reverses this: it reads the secret
            # value from Key Vault and writes it back to a file at ~/.secrets/,
            # then sets GITHUB_APP_PRIVATE_KEY_PATH to that file path.
            if ($envName -eq "GITHUB_APP_PRIVATE_KEY_PATH" -and (Test-Path $envValue)) {
                $envValue = Get-Content $envValue -Raw
                Write-Host "  Reading private key from file: $($matches[2])"
            }

            Write-Host "Setting: $secretName (from $envName)"
            & $az keyvault secret set --vault-name $VaultName --name $secretName --value $envValue --output none 2>&1 | Out-Null
        } else {
            Write-Warning "  Unmapped .env key: $envName (skipping)"
        }
    }
}

# Also store the WSL SQL password if not already set
$existing = & $az keyvault secret show --vault-name $VaultName --name "WslSqlPassword" --query "value" -o tsv 2>$null
if (-not $existing) {
    Write-Warning "WslSqlPassword not in Key Vault. Set it manually:"
    Write-Warning "  az keyvault secret set --vault-name $VaultName --name WslSqlPassword --value 'YOUR_PASSWORD'"
}

Write-Host "`nDone. $($secretMap.Count) secrets uploaded to $VaultName."
