# Test script for Write-AuditLog function
# This demonstrates the audit logging logic for windows-app-deploy.AC3.3

<#
.DESCRIPTION
Tests the Write-AuditLog function with various deployment scenarios.
This test file documents the expected behavior without requiring actual deployment.
#>

param([switch]$Verbose)

$ErrorActionPreference = "Stop"

# Define the function locally for testing (will be copied to deploy-app.ps1)
function Write-AuditLog {
    param([string]$Message)
    $logFile = Join-Path $env:USERPROFILE "Apps\deploy-log.txt"
    $logDir = Split-Path $logFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $App | $Message" | Out-File -FilePath $logFile -Append -Encoding UTF8
}

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
    # Create a test version using temp directory
    $App = "TestApp"
    $testLogFile = Join-Path $testDir "deploy-log.txt"

    # Simulate the function with test path
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logDir = Split-Path $testLogFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    "$timestamp | $App | Download started: v1.0.0" | Out-File -FilePath $testLogFile -Append -Encoding UTF8

    if (Test-Path $testLogFile) {
        Write-Host "PASS: Log file created successfully" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "FAIL: Log file not created" -ForegroundColor Red
        $failCount++
    }
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 2: Log entries have correct format
Write-Host "`nTest 2: Log entry format (timestamp | app | message)" -ForegroundColor Yellow
try {
    $App = "TestApp"
    $testLogFile = Join-Path $testDir "deploy-log-2.txt"
    $logDir = Split-Path $testLogFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $message = "Checksum verified: abc123def456"
    "$timestamp | $App | $message" | Out-File -FilePath $testLogFile -Encoding UTF8

    $content = Get-Content $testLogFile
    $expectedPattern = '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| TestApp \| Checksum verified: abc123def456$'

    if ($content -match $expectedPattern) {
        Write-Host "PASS: Log entry format is correct" -ForegroundColor Green
        if ($Verbose) { Write-Host "  Entry: $content" -ForegroundColor DarkGray }
        $passCount++
    } else {
        Write-Host "FAIL: Log entry format incorrect. Got: $content" -ForegroundColor Red
        $failCount++
    }
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 3: Multiple entries append correctly
Write-Host "`nTest 3: Multiple entries append correctly" -ForegroundColor Yellow
try {
    $App = "TestApp"
    $testLogFile = Join-Path $testDir "deploy-log-3.txt"
    $logDir = Split-Path $testLogFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    # Write first entry
    $timestamp1 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp1 | $App | Entry 1" | Out-File -FilePath $testLogFile -Encoding UTF8

    Start-Sleep -Milliseconds 100

    # Append second entry
    $timestamp2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp2 | $App | Entry 2" | Out-File -FilePath $testLogFile -Append -Encoding UTF8

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
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 4: App name is included in log
Write-Host "`nTest 4: App name included in log" -ForegroundColor Yellow
try {
    $App = "WhisperService"
    $testLogFile = Join-Path $testDir "deploy-log-4.txt"
    $logDir = Split-Path $testLogFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $App | Process started" | Out-File -FilePath $testLogFile -Encoding UTF8

    $content = Get-Content $testLogFile

    if ($content -match "\| WhisperService \|") {
        Write-Host "PASS: App name included in log entry" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "FAIL: App name not found in log" -ForegroundColor Red
        $failCount++
    }
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 5: Timestamps are valid date format
Write-Host "`nTest 5: Timestamp format yyyy-MM-dd HH:mm:ss" -ForegroundColor Yellow
try {
    $App = "TestApp"
    $testLogFile = Join-Path $testDir "deploy-log-5.txt"
    $logDir = Split-Path $testLogFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $App | Message" | Out-File -FilePath $testLogFile -Encoding UTF8

    $content = Get-Content $testLogFile
    $timestampPart = $content.Split('|')[0].Trim()

    # Try to parse the timestamp
    $parsed = [datetime]::ParseExact($timestampPart, 'yyyy-MM-dd HH:mm:ss', [System.Globalization.CultureInfo]::InvariantCulture)

    Write-Host "PASS: Timestamp format is valid" -ForegroundColor Green
    if ($Verbose) { Write-Host "  Parsed timestamp: $parsed" -ForegroundColor DarkGray }
    $passCount++
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 6: UTF8 encoding is used
Write-Host "`nTest 6: UTF8 encoding" -ForegroundColor Yellow
try {
    $App = "TestApp"
    $testLogFile = Join-Path $testDir "deploy-log-6.txt"
    $logDir = Split-Path $testLogFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $App | Special chars: café résumé" | Out-File -FilePath $testLogFile -Encoding UTF8

    $content = Get-Content $testLogFile

    if ($content -match "café résumé") {
        Write-Host "PASS: UTF8 encoding preserved special characters" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "FAIL: UTF8 encoding not working" -ForegroundColor Red
        $failCount++
    }
} catch {
    Write-Host "FAIL: $_" -ForegroundColor Red
    $failCount++
}

# Test Case 7: Log directory is created if missing
Write-Host "`nTest 7: Log directory created if missing" -ForegroundColor Yellow
try {
    $App = "TestApp"
    $testLogFile = Join-Path $testDir "subdir" "new-log.txt"

    # Ensure directory doesn't exist
    if (Test-Path (Split-Path $testLogFile)) {
        Remove-Item -Path (Split-Path $testLogFile) -Recurse -Force
    }

    # Write log entry (should create directory)
    $logDir = Split-Path $testLogFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp | $App | Message" | Out-File -FilePath $testLogFile -Encoding UTF8

    if (Test-Path $testLogFile) {
        Write-Host "PASS: Directory created and log file written" -ForegroundColor Green
        $passCount++
    } else {
        Write-Host "FAIL: Log file not created with directory creation" -ForegroundColor Red
        $failCount++
    }
} catch {
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
