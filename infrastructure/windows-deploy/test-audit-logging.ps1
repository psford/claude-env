# Test script for Write-AuditLog function
# This demonstrates the audit logging logic for windows-app-deploy.AC3.3

<#
.DESCRIPTION
Tests the Write-AuditLog function with various deployment scenarios.
This test file documents the expected behavior without requiring actual deployment.
#>

param([switch]$Verbose)

$ErrorActionPreference = "Stop"

# Dot-source the function from deploy-functions.ps1
. (Join-Path $PSScriptRoot "deploy-functions.ps1") -App "TestApp"

Write-Host "Testing Write-AuditLog function" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan

# Create a temporary test directory for isolated testing
$testDir = Join-Path ([System.IO.Path]::GetTempPath()) "audit-test-$(Get-Random)"
New-Item -ItemType Directory -Path $testDir -Force | Out-Null

$passCount = 0
$failCount = 0

# Test Case 1: Log file is created in correct location
Write-Host "`nTest 1: Log file creation" -ForegroundColor Yellow
try {
    # Override env to use test directory
    $originalProfile = $env:USERPROFILE
    $env:USERPROFILE = $testDir
    $App = "TestApp"

    # Call the actual Write-AuditLog function
    Write-AuditLog "Download started: v1.0.0"

    $testLogFile = Join-Path $testDir "Apps\deploy-log.txt"
    if (Test-Path $testLogFile) {
        Write-Host "PASS: Log file created successfully" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "FAIL: Log file not created" -ForegroundColor Red
        $failCount++
    }

    # Restore environment
    $env:USERPROFILE = $originalProfile
} catch {
    $env:USERPROFILE = $originalProfile
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 2: Log entries have correct format
Write-Host "`nTest 2: Log entry format (timestamp | app | message)" -ForegroundColor Yellow
try {
    # Override env to use test directory
    $originalProfile = $env:USERPROFILE
    $env:USERPROFILE = $testDir
    $App = "TestApp"

    # Call actual Write-AuditLog
    Write-AuditLog "Checksum verified: abc123def456"

    $testLogFile = Join-Path $testDir "Apps\deploy-log.txt"
    $content = Get-Content $testLogFile -Tail 1
    $expectedPattern = '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| TestApp \| Checksum verified: abc123def456$'

    if ($content -match $expectedPattern) {
        Write-Host "PASS: Log entry format is correct" -ForegroundColor Green
        if ($Verbose) { Write-Host "  Entry: $content" -ForegroundColor DarkGray }
        $passCount++
    } else {
        Write-Host "FAIL: Log entry format incorrect. Got: $content" -ForegroundColor Red
        $failCount++
    }

    # Restore environment
    $env:USERPROFILE = $originalProfile
} catch {
    $env:USERPROFILE = $originalProfile
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 3: Multiple entries append correctly
Write-Host "`nTest 3: Multiple entries append correctly" -ForegroundColor Yellow
try {
    # Override env to use test directory
    $originalProfile = $env:USERPROFILE
    $env:USERPROFILE = $testDir
    $App = "TestApp"

    # Remove old log file to start fresh
    $testLogFile = Join-Path $testDir "Apps\deploy-log.txt"
    if (Test-Path $testLogFile) {
        Remove-Item -Path $testLogFile -Force
    }

    # Call Write-AuditLog twice
    Write-AuditLog "Entry 1"
    Start-Sleep -Milliseconds 100
    Write-AuditLog "Entry 2"

    $lines = @(Get-Content $testLogFile)

    if ($lines.Count -eq 2 -and $lines[0] -match "Entry 1" -and $lines[1] -match "Entry 2") {
        Write-Host "PASS: Multiple entries appended correctly" -ForegroundColor Green
        if ($Verbose) {
            Write-Host "  Line 1: $($lines[0])" -ForegroundColor DarkGray
            Write-Host "  Line 2: $($lines[1])" -ForegroundColor DarkGray
        }
        $passCount++
    } else {
        Write-Host "FAIL: Entries not appended correctly" -ForegroundColor Red
        $failCount++
    }

    # Restore environment
    $env:USERPROFILE = $originalProfile
} catch {
    $env:USERPROFILE = $originalProfile
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 4: App name is included in log
Write-Host "`nTest 4: App name included in log" -ForegroundColor Yellow
try {
    # Override env to use test directory
    $originalProfile = $env:USERPROFILE
    $env:USERPROFILE = $testDir
    $App = "WhisperService"

    # Remove old log file to ensure we get the right entry
    $testLogFile = Join-Path $testDir "Apps\deploy-log.txt"
    if (Test-Path $testLogFile) {
        Remove-Item -Path $testLogFile -Force
    }

    # Call actual Write-AuditLog
    Write-AuditLog "Process started"

    $content = Get-Content $testLogFile
    if ($content -match "\| WhisperService \|") {
        Write-Host "PASS: App name included in log entry" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "FAIL: App name not found in log" -ForegroundColor Red
        $failCount++
    }

    # Restore environment
    $env:USERPROFILE = $originalProfile
} catch {
    $env:USERPROFILE = $originalProfile
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 5: Timestamps are valid date format
Write-Host "`nTest 5: Timestamp format yyyy-MM-dd HH:mm:ss" -ForegroundColor Yellow
try {
    # Override env to use test directory
    $originalProfile = $env:USERPROFILE
    $env:USERPROFILE = $testDir
    $App = "TestApp"

    # Remove old log file to ensure we get the right entry
    $testLogFile = Join-Path $testDir "Apps\deploy-log.txt"
    if (Test-Path $testLogFile) {
        Remove-Item -Path $testLogFile -Force
    }

    # Call actual Write-AuditLog
    Write-AuditLog "Message"

    $content = Get-Content $testLogFile
    $timestampPart = $content.Split('|')[0].Trim()

    # Try to parse the timestamp
    $parsed = [datetime]::ParseExact($timestampPart, 'yyyy-MM-dd HH:mm:ss', [System.Globalization.CultureInfo]::InvariantCulture)

    Write-Host "PASS: Timestamp format is valid" -ForegroundColor Green
    if ($Verbose) { Write-Host "  Parsed timestamp: $parsed" -ForegroundColor DarkGray }
    $passCount++

    # Restore environment
    $env:USERPROFILE = $originalProfile
} catch {
    $env:USERPROFILE = $originalProfile
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 6: UTF8 encoding is used
Write-Host "`nTest 6: UTF8 encoding" -ForegroundColor Yellow
try {
    # Override env to use test directory
    $originalProfile = $env:USERPROFILE
    $env:USERPROFILE = $testDir
    $App = "TestApp"

    # Remove old log file to ensure we get the right entry
    $testLogFile = Join-Path $testDir "Apps\deploy-log.txt"
    if (Test-Path $testLogFile) {
        Remove-Item -Path $testLogFile -Force
    }

    # Call actual Write-AuditLog with special characters
    Write-AuditLog "Special chars: café résumé"

    $content = Get-Content $testLogFile

    if ($content -match "café résumé") {
        Write-Host "PASS: UTF8 encoding preserved special characters" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "FAIL: UTF8 encoding not working" -ForegroundColor Red
        $failCount++
    }

    # Restore environment
    $env:USERPROFILE = $originalProfile
} catch {
    $env:USERPROFILE = $originalProfile
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 7: Log directory is created if missing
Write-Host "`nTest 7: Log directory created if missing" -ForegroundColor Yellow
try {
    # Override env to use test directory
    $originalProfile = $env:USERPROFILE
    $env:USERPROFILE = $testDir
    $App = "TestApp"

    # Remove the Apps directory to force the function to create it
    $appsDir = Join-Path $testDir "Apps"
    if (Test-Path $appsDir) {
        Remove-Item -Path $appsDir -Recurse -Force
    }

    # Call Write-AuditLog which should create the directory
    Write-AuditLog "Message"

    $testLogFile = Join-Path $testDir "Apps\deploy-log.txt"
    if (Test-Path $testLogFile) {
        Write-Host "PASS: Directory created and log file written" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "FAIL: Log file not created with directory creation" -ForegroundColor Red
        $failCount++
    }

    # Restore environment
    $env:USERPROFILE = $originalProfile
} catch {
    $env:USERPROFILE = $originalProfile
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Cleanup
Write-Host "`nCleaning up test files..." -ForegroundColor Gray
Remove-Item -Path $testDir -Recurse -Force -ErrorAction SilentlyContinue

# Summary
Write-Host "`n===============================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host "Passed: $passCount" -ForegroundColor Green
Write-Host "Failed: $failCount" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Red" })

if ($failCount -eq 0) {
    Write-Host "`nAll tests passed! Audit logging logic is working correctly." -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nSome tests failed." -ForegroundColor Red
    exit 1
}
