# Human Test Plan: Windows App Deployment Pipeline

**Implementation plan:** `docs/implementation-plans/2026-03-26-windows-app-deploy/`
**Date:** 2026-03-27
**Environment:** Windows 10/11 with PowerShell 5.1+, GitHub CLI (`gh`) authenticated

---

## Already Verified (no action needed)

These were verified during implementation — automated tests pass and code review confirmed correctness:

| AC | What | How Verified |
|----|------|-------------|
| AC1.5 | Vulnerability scan job exists | Python test (passed in WSL2) |
| AC1.6 | All GitHub Actions pinned by SHA | Python test (passed in WSL2) |
| AC2.6 | Path validation prevents writes outside install dir | PowerShell test + code review (3 review cycles) |
| AC3.3 | Audit logging at all deploy steps | PowerShell test + code review confirmed 17+ log points |
| AC3.4 | Process not running handled gracefully | Code review confirmed Get-Process with SilentlyContinue |
| AC5.1 | New app = registry + workflow + .bat only | Code review confirmed SysTTS required zero script changes |

---

## Prerequisites

- [ ] GitHub CLI installed and authenticated (`gh auth status`)
- [ ] claude-env repo checked out with latest develop branch

---

## Test 1: CI Workflow (do this first — creates the releases needed for later tests)

### 1a: Trigger CI for whisper-service (AC1.1)

1. Merge whisper-service develop → main PR
2. Check GitHub Actions tab

- [ ] `Build and Release` workflow triggers on `windows-latest`
- [ ] Vulnerability scan job runs first
- [ ] Build + release job runs after scan passes
- [ ] Release created with 3 assets (zip, sha256, appsettings.default.json)

### 1b: Trigger CI for SysTTS (AC1.1)

Same process for SysTTS repo.

- [ ] Release created with 3 assets

### 1c: Verify release contents (AC1.2, AC1.3, AC1.4)

After a release exists, spot-check one:

```powershell
$tempDir = "$env:TEMP\release-test"
mkdir $tempDir -Force
gh release download --pattern '*.zip' -R psford/whisper-service -D $tempDir
gh release download --pattern '*.sha256' -R psford/whisper-service -D $tempDir
gh release download --pattern 'appsettings.default.json' -R psford/whisper-service -D $tempDir

# Checksum matches?
$zip = Get-ChildItem "$tempDir\*.zip"
$computed = (Get-FileHash $zip.FullName -Algorithm SHA256).Hash.ToLower()
$expected = ((Get-Content "$tempDir\*.sha256") -split '\s+')[0]
Write-Host "Checksum: $(if ($computed -eq $expected) {'PASS'} else {'FAIL'})"

# Zip excludes config/models?
Expand-Archive $zip.FullName "$tempDir\extracted"
Write-Host "appsettings.json excluded: $(if (-not (Test-Path "$tempDir\extracted\appsettings.json")) {'PASS'} else {'FAIL'})"
Write-Host "models/ excluded: $(if (-not (Test-Path "$tempDir\extracted\models")) {'PASS'} else {'FAIL'})"
Write-Host "appsettings.default.json present: $(if (Test-Path "$tempDir\appsettings.default.json") {'PASS'} else {'FAIL'})"

Remove-Item $tempDir -Recurse
```

- [ ] Checksum matches
- [ ] `appsettings.json` and `models/` NOT in zip
- [ ] `appsettings.default.json` available as separate asset

---

## Test 2: Bootstrap (AC4.1, AC4.2, AC4.3)

### 2a: First-time bootstrap

```powershell
cd C:\path\to\claude-env\infrastructure\windows-deploy
powershell -ExecutionPolicy Bypass -File bootstrap-deploy.ps1
```

- [ ] `%USERPROFILE%\tools\deploy-app.ps1` exists
- [ ] `%USERPROFILE%\tools\deploy-functions.ps1` exists
- [ ] `%USERPROFILE%\tools\app-registry.json` exists
- [ ] `Deploy whisper-service.bat` appears on Desktop
- [ ] `Deploy systts.bat` appears on Desktop

### 2b: Run bootstrap again (idempotency)

- [ ] No errors, output shows "Skipped" for existing .bat files

---

## Test 3: First Deploy — whisper-service (AC2.1, AC2.3, AC2.7)

Delete `%USERPROFILE%\Apps\WhisperService\` if it exists, then double-click `Deploy whisper-service.bat` on Desktop.

- [ ] cmd.exe window opens with deploy output visible
- [ ] Release downloaded and checksum verified
- [ ] App extracted to `%USERPROFILE%\Apps\WhisperService\`
- [ ] Default `appsettings.json` created (first install)
- [ ] Model downloaded from Hugging Face
- [ ] WhisperService process started
- [ ] `%USERPROFILE%\Apps\deploy-log.txt` created with timestamped entries
- [ ] Window stays open at "pause" prompt

---

## Test 4: Update Deploy — config preserved (AC2.2)

1. Edit `%USERPROFILE%\Apps\WhisperService\appsettings.json` — add a comment or change a value
2. Double-click `Deploy whisper-service.bat` again

- [ ] Deploy completes
- [ ] Your edit is preserved in `appsettings.json`
- [ ] Models directory preserved

---

## Test 5: SysTTS Deploy (AC5.2, AC5.3)

Double-click `Deploy systts.bat` on Desktop.

- [ ] SysTTS downloads and installs to `%USERPROFILE%\Apps\SysTTS\`
- [ ] Piper voice models downloaded (2 files from Hugging Face)
- [ ] espeak-ng-data downloaded and extracted
- [ ] SysTTS process started
- [ ] WhisperService directory untouched (app isolation)

---

## Test 6: Rollback (AC3.1) — optional but recommended

After a successful deploy, test failure recovery:

1. Deploy whisper-service normally (so backup exists)
2. Tamper with checksum — see `docs/test-plans/2026-03-27-rollback-verification.md` for steps

- [ ] Deploy detects mismatch and aborts
- [ ] Previous version restored (binaries + config)
- [ ] Audit log records failure and rollback

---

## Results

| Test | Pass/Fail | Notes |
|------|-----------|-------|
| 1a: CI whisper-service | | |
| 1b: CI SysTTS | | |
| 1c: Release contents | | |
| 2a: Bootstrap | | |
| 2b: Bootstrap idempotency | | |
| 3: First deploy | | |
| 4: Update deploy | | |
| 5: SysTTS deploy | | |
| 6: Rollback (optional) | | |

**Tester:** _______________  **Date:** _______________
