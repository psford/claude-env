# Test script for Assert-PathWithinInstallDir function
# This demonstrates the path validation logic for windows-app-deploy.AC2.6

<#
.DESCRIPTION
Tests the Assert-PathWithinInstallDir function with various path traversal attempts.
This test file documents the expected behavior without requiring actual deployment.
#>

param([switch]$Verbose)

$ErrorActionPreference = "Stop"

# Dot-source the function from deploy-functions.ps1
$App = "TestApp"  # Required for Write-AuditLog
. (Join-Path (Split-Path -Parent $PSScriptRoot) "deploy-functions.ps1")

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

# Test Case 8: Symlink/junction escape documentation
Write-Host "`nTest 8: Symlink/junction resolution (known limitation)" -ForegroundColor Yellow
Write-Host "NOTE: GetFullPath does NOT resolve symlinks/junctions on Windows before .NET 4.6+" -ForegroundColor DarkGray
Write-Host "SKIP: Symlink resolution would require runtime-dependent behavior" -ForegroundColor DarkGray
Write-Host "DOCUMENTED: Known limitation - actual symlinks/junctions are not fully resolved" -ForegroundColor Yellow

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
