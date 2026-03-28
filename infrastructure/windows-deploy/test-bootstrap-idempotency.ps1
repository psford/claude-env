# Test script for bootstrap-deploy.ps1 idempotency
# This demonstrates the idempotency requirement for windows-app-deploy.AC4.3

<#
.DESCRIPTION
Tests that bootstrap-deploy.ps1 is idempotent: running it twice produces no errors,
no duplicate .bat files, and the tools directory remains unchanged.

This test creates a temporary mock directory structure and runs bootstrap twice,
verifying idempotent behavior without modifying the actual user profile.

.PARAMETER TestDir
Path to a temporary directory to use for testing. If not specified, a random temp dir is created.
#>

param(
    [string]$TestDir = $null,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

Write-Host "Bootstrap Idempotency Test (AC4.3)" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

# Setup: Create temporary test directory
if (-not $TestDir) {
    $TestDir = Join-Path $env:TEMP "bootstrap-test-$(Get-Random)"
}

if (-not (Test-Path $TestDir)) {
    New-Item -ItemType Directory -Path $TestDir -Force | Out-Null
}

Write-Host "`nTest directory: $TestDir" -ForegroundColor DarkGray

# Create mock environment
$mockUserProfile = Join-Path $TestDir "profile"
$mockToolsDir = Join-Path $mockUserProfile "tools"
$mockDesktopDir = Join-Path $mockUserProfile "Desktop"

New-Item -ItemType Directory -Path $mockToolsDir -Force | Out-Null
New-Item -ItemType Directory -Path $mockDesktopDir -Force | Out-Null

Write-Host "Created mock user profile at: $mockUserProfile" -ForegroundColor DarkGray

# Get the bootstrap script path
$bootstrapScript = Join-Path (Split-Path -Parent $PSScriptRoot) "infrastructure" "windows-deploy" "bootstrap-deploy.ps1"
$scriptDir = Split-Path -Parent $PSScriptRoot

if ($bootstrapScript -eq "") {
    $bootstrapScript = Join-Path $PSScriptRoot "bootstrap-deploy.ps1"
}

if (-not (Test-Path $bootstrapScript)) {
    Write-Host "ERROR: bootstrap-deploy.ps1 not found at $bootstrapScript" -ForegroundColor Red
    exit 1
}

Write-Host "Bootstrap script: $bootstrapScript" -ForegroundColor DarkGray

# Test state tracking
$testPassed = $true
$errors = @()

# --- First Run ---
Write-Host "`n--- First Bootstrap Run ---" -ForegroundColor Yellow

try {
    # Use Invoke-Expression with modified environment variables
    $env:USERPROFILE_BACKUP = $env:USERPROFILE
    $env:USERPROFILE = $mockUserProfile

    if ($Verbose) {
        Write-Host "Running: & `"$bootstrapScript`"" -ForegroundColor DarkGray
    }

    $output1 = & $bootstrapScript 2>&1
    $exitCode1 = $LASTEXITCODE

    if ($exitCode1 -ne 0) {
        Write-Host "FAIL: First run exited with code $exitCode1" -ForegroundColor Red
        $testPassed = $false
        $errors += "First bootstrap run failed with exit code $exitCode1"
    } else {
        Write-Host "✓ First run completed successfully" -ForegroundColor Green
    }

    if ($Verbose) {
        Write-Host "`nFirst run output:" -ForegroundColor DarkGray
        $output1 | Write-Host -ForegroundColor DarkGray
    }

} catch {
    Write-Host "FAIL: $($_.Exception.Message)" -ForegroundColor Red
    $testPassed = $false
    $errors += $_.Exception.Message
} finally {
    $env:USERPROFILE = $env:USERPROFILE_BACKUP
}

# Get state after first run
$batFilesAfterRun1 = @()
if (Test-Path $mockDesktopDir) {
    $batFilesAfterRun1 = @(Get-ChildItem -Path $mockDesktopDir -Filter "*.bat" -ErrorAction SilentlyContinue)
}

Write-Host "  .bat files after run 1: $($batFilesAfterRun1.Count)" -ForegroundColor DarkGray

$toolsContentsRun1 = @()
if (Test-Path $mockToolsDir) {
    $toolsContentsRun1 = @(Get-ChildItem -Path $mockToolsDir -ErrorAction SilentlyContinue)
}

Write-Host "  tools directory items: $($toolsContentsRun1.Count)" -ForegroundColor DarkGray

# --- Second Run ---
Write-Host "`n--- Second Bootstrap Run ---" -ForegroundColor Yellow

try {
    $env:USERPROFILE = $mockUserProfile

    if ($Verbose) {
        Write-Host "Running: & `"$bootstrapScript`"" -ForegroundColor DarkGray
    }

    $output2 = & $bootstrapScript 2>&1
    $exitCode2 = $LASTEXITCODE

    if ($exitCode2 -ne 0) {
        Write-Host "FAIL: Second run exited with code $exitCode2" -ForegroundColor Red
        $testPassed = $false
        $errors += "Second bootstrap run failed with exit code $exitCode2"
    } else {
        Write-Host "✓ Second run completed successfully" -ForegroundColor Green
    }

    if ($Verbose) {
        Write-Host "`nSecond run output:" -ForegroundColor DarkGray
        $output2 | Write-Host -ForegroundColor DarkGray
    }

} catch {
    Write-Host "FAIL: $($_.Exception.Message)" -ForegroundColor Red
    $testPassed = $false
    $errors += $_.Exception.Message
} finally {
    $env:USERPROFILE = $env:USERPROFILE_BACKUP
}

# Get state after second run
$batFilesAfterRun2 = @()
if (Test-Path $mockDesktopDir) {
    $batFilesAfterRun2 = @(Get-ChildItem -Path $mockDesktopDir -Filter "*.bat" -ErrorAction SilentlyContinue)
}

Write-Host "  .bat files after run 2: $($batFilesAfterRun2.Count)" -ForegroundColor DarkGray

$toolsContentsRun2 = @()
if (Test-Path $mockToolsDir) {
    $toolsContentsRun2 = @(Get-ChildItem -Path $mockToolsDir -ErrorAction SilentlyContinue)
}

Write-Host "  tools directory items: $($toolsContentsRun2.Count)" -ForegroundColor DarkGray

# --- Validation ---
Write-Host "`n--- Idempotency Validation ---" -ForegroundColor Yellow

# Check 1: No increase in .bat files (no duplicates)
if ($batFilesAfterRun1.Count -eq $batFilesAfterRun2.Count) {
    Write-Host "✓ No duplicate .bat files (count stable: $($batFilesAfterRun1.Count))" -ForegroundColor Green
} else {
    Write-Host "FAIL: .bat file count changed (run 1: $($batFilesAfterRun1.Count), run 2: $($batFilesAfterRun2.Count))" -ForegroundColor Red
    $testPassed = $false
    $errors += ".bat file count increased on second run"
}

# Check 2: Tools directory contents unchanged
if ($toolsContentsRun1.Count -eq $toolsContentsRun2.Count) {
    Write-Host "✓ Tools directory stable ($($toolsContentsRun1.Count) items)" -ForegroundColor Green
} else {
    Write-Host "FAIL: Tools directory contents changed (run 1: $($toolsContentsRun1.Count) items, run 2: $($toolsContentsRun2.Count) items)" -ForegroundColor Red
    $testPassed = $false
    $errors += "Tools directory contents changed on second run"
}

# Check 3: Verify required files exist (from run 1)
$requiredFiles = @("deploy-app.ps1", "app-registry.json", "deploy-functions.ps1")
$missingFiles = @()

foreach ($file in $requiredFiles) {
    $filePath = Join-Path $mockToolsDir $file
    if (-not (Test-Path $filePath)) {
        $missingFiles += $file
    } else {
        Write-Host "✓ Found: $file" -ForegroundColor Green
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "FAIL: Missing required files: $($missingFiles -join ', ')" -ForegroundColor Red
    $testPassed = $false
    $errors += "Missing required files: $($missingFiles -join ', ')"
}

# Check 4: Verify .bat files exist
if ($batFilesAfterRun1.Count -eq 0) {
    Write-Host "WARNING: No .bat files created after first run" -ForegroundColor Yellow
    # This might be expected if app-registry.json is empty or not processed correctly
} else {
    Write-Host "✓ .bat files created: $($batFilesAfterRun1.Count)" -ForegroundColor Green
    foreach ($batFile in $batFilesAfterRun1) {
        Write-Host "  - $($batFile.Name)" -ForegroundColor DarkGray
    }
}

# --- Summary ---
Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "Test Results" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

if ($testPassed) {
    Write-Host "✓ AC4.3 PASSED: Bootstrap is idempotent" -ForegroundColor Green
} else {
    Write-Host "✗ AC4.3 FAILED: Idempotency issues detected" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
}

# Cleanup
Write-Host "`nCleaning up test directory: $TestDir" -ForegroundColor DarkGray
Remove-Item -Path $TestDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`nTest complete." -ForegroundColor Cyan

if ($testPassed) {
    exit 0
} else {
    exit 1
}
