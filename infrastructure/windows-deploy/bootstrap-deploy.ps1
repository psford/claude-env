param()

$ErrorActionPreference = "Stop"

# ============================================================================
# INITIALIZATION
# ============================================================================

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "Bootstrap Deploy Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "Script location: $scriptDir" -ForegroundColor Cyan
Write-Host ""

$toolsDir = Join-Path $env:USERPROFILE "tools"
$deployScriptSource = Join-Path $scriptDir "deploy-app.ps1"
$deployFunctionsSource = Join-Path $scriptDir "deploy-functions.ps1"
$registrySource = Join-Path $scriptDir "app-registry.json"
$templateSource = Join-Path $scriptDir "Deploy-App.bat.template"
$desktopDir = [Environment]::GetFolderPath('Desktop')

Write-Host "Target paths:" -ForegroundColor Cyan
Write-Host "  Tools directory: $toolsDir" -ForegroundColor Cyan
Write-Host "  Desktop directory: $desktopDir" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# PREREQUISITES CHECK
# ============================================================================

Write-Host "Checking prerequisites..." -ForegroundColor Cyan

$ghCommand = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghCommand) {
    Write-Host "error: gh CLI not found" -ForegroundColor Red
    Write-Host "Install with: winget install GitHub.cli" -ForegroundColor Yellow
    exit 1
}
Write-Host "  gh CLI found: $($ghCommand.Source)" -ForegroundColor Green

# Check gh authentication status
try {
    $authStatus = & gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "error: gh CLI not authenticated" -ForegroundColor Red
        Write-Host "Authenticate with: gh auth login" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  gh CLI authenticated" -ForegroundColor Green
} catch {
    Write-Host "error: failed to check gh authentication: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Prerequisites OK" -ForegroundColor Green
Write-Host ""

# ============================================================================
# CREATE TOOLS DIRECTORY
# ============================================================================

Write-Host "Setting up tools directory..." -ForegroundColor Cyan

if (-not (Test-Path $toolsDir)) {
    New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
    Write-Host "  Created: $toolsDir" -ForegroundColor Green
} else {
    Write-Host "  Already exists: $toolsDir" -ForegroundColor Green
}

# ============================================================================
# COPY FILES TO TOOLS DIRECTORY
# ============================================================================

Write-Host "Copying deployment scripts..." -ForegroundColor Cyan

try {
    # Copy deploy-app.ps1
    if (Test-Path $deployScriptSource) {
        Copy-Item -Path $deployScriptSource -Destination $toolsDir -Force
        Write-Host "  Copied: deploy-app.ps1" -ForegroundColor Green
    } else {
        throw "deploy-app.ps1 not found at $deployScriptSource"
    }

    # Copy deploy-functions.ps1
    if (Test-Path $deployFunctionsSource) {
        Copy-Item -Path $deployFunctionsSource -Destination $toolsDir -Force
        Write-Host "  Copied: deploy-functions.ps1" -ForegroundColor Green
    } else {
        throw "deploy-functions.ps1 not found at $deployFunctionsSource"
    }

    # Copy app-registry.json
    if (Test-Path $registrySource) {
        Copy-Item -Path $registrySource -Destination $toolsDir -Force
        Write-Host "  Copied: app-registry.json" -ForegroundColor Green
    } else {
        throw "app-registry.json not found at $registrySource"
    }

    # Copy template for reference (not strictly necessary but helpful)
    if (Test-Path $templateSource) {
        Copy-Item -Path $templateSource -Destination $toolsDir -Force
        Write-Host "  Copied: Deploy-App.bat.template" -ForegroundColor Green
    }
} catch {
    Write-Host "error: failed to copy files: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ============================================================================
# CREATE DESKTOP SHORTCUTS
# ============================================================================

Write-Host "Creating desktop shortcuts..." -ForegroundColor Cyan

$registryPath = Join-Path $toolsDir "app-registry.json"

try {
    if (-not (Test-Path $registryPath)) {
        throw "app-registry.json not found at $registryPath"
    }

    $registry = Get-Content $registryPath | ConvertFrom-Json

    $appsCreated = 0
    $appsSkipped = 0

    foreach ($appKey in $registry.PSObject.Properties.Name) {
        $appConfig = $registry.$appKey

        # Create .bat filename from app key
        $batFilename = "Deploy $appKey.bat"
        $batPath = Join-Path $desktopDir $batFilename

        if (Test-Path $batPath) {
            Write-Host "  Skipped (already exists): $batFilename" -ForegroundColor Yellow
            $appsSkipped++
        } else {
            # Read template and replace {APP_NAME}
            $templatePath = Join-Path $toolsDir "Deploy-App.bat.template"
            if (Test-Path $templatePath) {
                $batContent = Get-Content $templatePath -Raw
                $batContent = $batContent -replace '{APP_NAME}', $appKey
            } else {
                # Fallback if template not in tools (shouldn't happen)
                $batContent = @"
@echo off
title Deploy $appKey
echo ========================================
echo   Deploying $appKey
echo ========================================
echo.
powershell -ExecutionPolicy Bypass -File "%USERPROFILE%\tools\deploy-app.ps1" -App $appKey
echo.
if %ERRORLEVEL% EQU 0 (
    echo Deploy complete.
) else (
    echo Deploy FAILED. Check output above.
)
echo.
pause
"@
            }

            Set-Content -Path $batPath -Value $batContent -Encoding ASCII
            Write-Host "  Created: $batFilename" -ForegroundColor Cyan
            $appsCreated++
        }
    }

    Write-Host ""
    Write-Host "Shortcut creation summary:" -ForegroundColor Green
    Write-Host "  Created: $appsCreated" -ForegroundColor Green
    Write-Host "  Skipped: $appsSkipped" -ForegroundColor Yellow

} catch {
    Write-Host "error: failed to create shortcuts: $_" -ForegroundColor Red
    exit 1
}

# ============================================================================
# SUCCESS
# ============================================================================

Write-Host ""
Write-Host "Bootstrap complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Check Desktop for Deploy *.bat files" -ForegroundColor Cyan
Write-Host "  2. Double-click a .bat file to deploy an app" -ForegroundColor Cyan
Write-Host "  3. To re-run bootstrap, simply run this script again" -ForegroundColor Cyan
Write-Host ""

exit 0
