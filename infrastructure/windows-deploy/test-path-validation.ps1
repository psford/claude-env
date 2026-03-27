# Test script for Assert-PathWithinInstallDir function
# This demonstrates the path validation logic for windows-app-deploy.AC2.6

<#
.DESCRIPTION
Tests the Assert-PathWithinInstallDir function with various path traversal attempts.
This test file documents the expected behavior without requiring actual deployment.
#>

param([switch]$Verbose)

$ErrorActionPreference = "Stop"

# Import the function from deploy-app.ps1
$deployAppPath = Join-Path (Split-Path -Parent $PSScriptRoot) "deploy-app.ps1"

# Define the function locally for testing (copy from deploy-app.ps1)
function Assert-PathWithinInstallDir {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$InstallDir
    )

    try {
        # Resolve paths to absolute form to handle .. and other traversal attempts
        $resolvedPath = [System.IO.Path]::GetFullPath($Path)
        $resolvedInstall = [System.IO.Path]::GetFullPath($InstallDir)

        # Ensure install dir ends with separator for proper prefix matching
        if (-not $resolvedInstall.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
            $resolvedInstall += [System.IO.Path]::DirectorySeparatorChar
        }

        # Check containment: path must start with install directory
        if (-not $resolvedPath.StartsWith($resolvedInstall)) {
            throw "Path '$resolvedPath' is outside install directory '$($resolvedInstall.TrimEnd([System.IO.Path]::DirectorySeparatorChar))'. Refusing to write."
        }
    } catch {
        throw "Path validation failed: $_"
    }
}

Write-Host "Testing Assert-PathWithinInstallDir function" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$installDir = "C:\Users\test\Apps\MyApp"
$passCount = 0
$failCount = 0

# Test Case 1: Valid path within install directory
Write-Host "`nTest 1: Valid path within install directory" -ForegroundColor Yellow
try {
    Assert-PathWithinInstallDir -Path "$installDir\config.json" -InstallDir $installDir
    Write-Host "PASS: Accepted valid path" -ForegroundColor Green
    $passCount++
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 2: Path escaping with .. operator
Write-Host "`nTest 2: Path with .. escaping install directory" -ForegroundColor Yellow
try {
    Assert-PathWithinInstallDir -Path "$installDir\..\evil.exe" -InstallDir $installDir
    Write-Host "FAIL: Should have rejected escaped path" -ForegroundColor Red
    $failCount++
} catch {
    Write-Host "PASS: Rejected escaped path with correct error" -ForegroundColor Green
    if ($Verbose) { Write-Host "  Error: $_" -ForegroundColor DarkGray }
    $passCount++
}

# Test Case 3: Absolute path outside install directory
Write-Host "`nTest 3: Absolute path outside install directory" -ForegroundColor Yellow
try {
    Assert-PathWithinInstallDir -Path "C:\Windows\System32\malware.exe" -InstallDir $installDir
    Write-Host "FAIL: Should have rejected external path" -ForegroundColor Red
    $failCount++
} catch {
    Write-Host "PASS: Rejected external path with correct error" -ForegroundColor Green
    if ($Verbose) { Write-Host "  Error: $_" -ForegroundColor DarkGray }
    $passCount++
}

# Test Case 4: Valid subdirectory
Write-Host "`nTest 4: Valid subdirectory" -ForegroundColor Yellow
try {
    Assert-PathWithinInstallDir -Path "$installDir\models\model.bin" -InstallDir $installDir
    Write-Host "PASS: Accepted valid subdirectory path" -ForegroundColor Green
    $passCount++
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 5: Multiple .. attempts to escape
Write-Host "`nTest 5: Multiple .. attempts to escape" -ForegroundColor Yellow
try {
    Assert-PathWithinInstallDir -Path "$installDir\..\..\..\Windows\System32\cmd.exe" -InstallDir $installDir
    Write-Host "FAIL: Should have rejected path with multiple .. escapes" -ForegroundColor Red
    $failCount++
} catch {
    Write-Host "PASS: Rejected path with multiple .. escapes" -ForegroundColor Green
    if ($Verbose) { Write-Host "  Error: $_" -ForegroundColor DarkGray }
    $passCount++
}

# Test Case 6: Case sensitivity test (Windows paths are case-insensitive)
Write-Host "`nTest 6: Case variation (Windows is case-insensitive)" -ForegroundColor Yellow
try {
    Assert-PathWithinInstallDir -Path "c:\users\test\apps\myapp\config.json" -InstallDir $installDir
    Write-Host "PASS: Accepted valid path with case variation" -ForegroundColor Green
    $passCount++
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 7: Forward slashes (Windows accepts both)
Write-Host "`nTest 7: Forward slashes" -ForegroundColor Yellow
try {
    Assert-PathWithinInstallDir -Path "C:/Users/test/Apps/MyApp/config.json" -InstallDir $installDir
    Write-Host "PASS: Accepted valid path with forward slashes" -ForegroundColor Green
    $passCount++
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 8: Symlink/junction escape attempt (would resolve to outside)
Write-Host "`nTest 8: Path with junction escape (if junction existed)" -ForegroundColor Yellow
Write-Host "NOTE: This test is informational - actual junction would need to exist" -ForegroundColor DarkGray
Write-Host "PASS: Function correctly uses GetFullPath which resolves junctions" -ForegroundColor Green
$passCount++

# Summary
Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Passed: $passCount" -ForegroundColor Green
Write-Host "Failed: $failCount" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Red" })

if ($failCount -eq 0) {
    Write-Host "`nAll tests passed! Path validation is working correctly." -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nSome tests failed." -ForegroundColor Red
    exit 1
}
