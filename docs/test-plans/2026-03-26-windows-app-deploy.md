# Human Test Plan: Windows App Deployment Pipeline

**Implementation plan:** `docs/implementation-plans/2026-03-26-windows-app-deploy/`
**Date:** 2026-03-27
**Environment:** Windows 10/11 with PowerShell 5.1+, GitHub CLI (`gh`) authenticated

---

## Prerequisites

- [ ] GitHub CLI installed and authenticated (`gh auth status`)
- [ ] whisper-service repo has at least one CI-produced release on GitHub
- [ ] SysTTS repo has at least one CI-produced release on GitHub
- [ ] No prior installations in `%USERPROFILE%\Apps\` (clean state preferred)
- [ ] claude-env repo checked out with latest develop branch

---

## Part 1: Automated Tests (run first)

### Python tests (run from WSL2 or any Python 3 environment)

```bash
cd /home/patrick/projects/claude-env
python3 infrastructure/windows-deploy/tests/test_workflow_actions.py
```

**Expected:** All tests pass (AC1.5 vulnerability scan job, AC1.6 SHA-pinned actions).

### PowerShell tests (run on Windows)

```powershell
cd infrastructure\windows-deploy
powershell -ExecutionPolicy Bypass -File test-path-validation.ps1
powershell -ExecutionPolicy Bypass -File test-audit-logging.ps1
powershell -ExecutionPolicy Bypass -File test-bootstrap-idempotency.ps1
```

**Expected:** All tests pass (AC2.6 path validation, AC3.3 audit logging, AC4.3 idempotency).

---

## Part 2: Bootstrap and Desktop Integration

### Test 2.1: First-time bootstrap (AC4.1, AC4.2)

```powershell
cd C:\path\to\claude-env\infrastructure\windows-deploy
powershell -ExecutionPolicy Bypass -File bootstrap-deploy.ps1
```

- [ ] `%USERPROFILE%\tools\deploy-app.ps1` exists
- [ ] `%USERPROFILE%\tools\deploy-functions.ps1` exists
- [ ] `%USERPROFILE%\tools\app-registry.json` exists
- [ ] `Deploy whisper-service.bat` appears on Desktop
- [ ] `Deploy systts.bat` appears on Desktop
- [ ] Output shows green "Created" messages

### Test 2.2: Bootstrap idempotency (AC4.3)

Run bootstrap again:
```powershell
powershell -ExecutionPolicy Bypass -File bootstrap-deploy.ps1
```

- [ ] No errors
- [ ] Output shows yellow "Skipped" for existing .bat files
- [ ] Tools directory files updated (overwritten with latest)
- [ ] No duplicate .bat files on Desktop

### Test 2.3: Desktop shortcut runs deploy (AC4.1)

Double-click `Deploy whisper-service.bat` on Desktop.

- [ ] cmd.exe window opens with title "Deploy whisper-service"
- [ ] Deploy output visible in terminal
- [ ] Window stays open at "pause" prompt after completion

---

## Part 3: Whisper-Service Deploy

### Test 3.1: First-time deploy (AC2.1, AC2.3, AC2.7)

If `%USERPROFILE%\Apps\WhisperService\` exists, delete it first.

```powershell
cd %USERPROFILE%\tools
powershell -ExecutionPolicy Bypass -File deploy-app.ps1 -App whisper-service
```

- [ ] Release downloaded from GitHub
- [ ] Provenance check passes (github-actions[bot])
- [ ] SHA256 checksum verified
- [ ] App extracted to `%USERPROFILE%\Apps\WhisperService\`
- [ ] Default `appsettings.json` installed from `appsettings.default.json`
- [ ] Model downloaded from Hugging Face
- [ ] WhisperService process started and running
- [ ] Audit log created at `%USERPROFILE%\Apps\deploy-log.txt`

### Test 3.2: Update deploy preserves config (AC2.2)

1. Edit `%USERPROFILE%\Apps\WhisperService\appsettings.json` — add a sentinel comment
2. Run deploy again:
```powershell
powershell -ExecutionPolicy Bypass -File deploy-app.ps1 -App whisper-service
```

- [ ] Deploy completes successfully
- [ ] Sentinel comment preserved in `appsettings.json`
- [ ] Models directory preserved
- [ ] New binaries extracted

### Test 3.3: Checksum verification (AC1.2, AC2.4)

After a successful deploy, verify the release assets:

```powershell
$tempDir = "$env:TEMP\checksum-test"
mkdir $tempDir -Force
gh release download --pattern '*.zip' -R psford/whisper-service -D $tempDir
gh release download --pattern '*.sha256' -R psford/whisper-service -D $tempDir
$zip = Get-ChildItem "$tempDir\*.zip"
$sha = Get-Content "$tempDir\*.sha256"
$computed = (Get-FileHash $zip.FullName -Algorithm SHA256).Hash.ToLower()
$expected = ($sha -split '\s+')[0]
if ($computed -eq $expected) { Write-Host "PASS: Checksum matches" } else { Write-Host "FAIL: Mismatch" }
Remove-Item $tempDir -Recurse
```

- [ ] Checksum matches

### Test 3.4: Release excludes config/models (AC1.3, AC1.4)

```powershell
$tempDir = "$env:TEMP\release-contents-test"
mkdir $tempDir -Force
gh release download --pattern '*.zip' -R psford/whisper-service -D $tempDir
$zip = Get-ChildItem "$tempDir\*.zip"
Expand-Archive $zip.FullName "$tempDir\extracted"
Test-Path "$tempDir\extracted\appsettings.json"       # Should be False
Test-Path "$tempDir\extracted\models"                  # Should be False
gh release download --pattern 'appsettings.default.json' -R psford/whisper-service -D $tempDir
Test-Path "$tempDir\appsettings.default.json"          # Should be True
Remove-Item $tempDir -Recurse
```

- [ ] `appsettings.json` NOT in zip
- [ ] `models/` NOT in zip
- [ ] `appsettings.default.json` available as separate asset

### Test 3.5: Tampered checksum rejected (AC2.5)

```powershell
# Deploy normally first (to have a working backup)
# Then tamper with checksum during next deploy attempt
# See docs/test-plans/2026-03-27-rollback-verification.md for detailed steps
```

- [ ] Deploy detects mismatch and aborts
- [ ] Previous version restored from backup
- [ ] Audit log records failure

---

## Part 4: SysTTS Deploy

### Test 4.1: SysTTS first deploy (AC5.2, AC5.3)

```powershell
powershell -ExecutionPolicy Bypass -File deploy-app.ps1 -App systts
```

- [ ] SysTTS release downloaded
- [ ] Piper voice models downloaded from Hugging Face (2 files)
- [ ] espeak-ng-data downloaded and extracted from GitHub release
- [ ] SysTTS installed to `%USERPROFILE%\Apps\SysTTS\` (separate from WhisperService)
- [ ] SysTTS process started

### Test 4.2: App isolation (AC5.3)

- [ ] `%USERPROFILE%\Apps\WhisperService\` has whisper-service binaries + config
- [ ] `%USERPROFILE%\Apps\SysTTS\` has SysTTS binaries + config
- [ ] No cross-contamination (SysTTS files NOT in WhisperService dir, and vice versa)
- [ ] Both apps run independently

---

## Part 5: Error Recovery

### Test 5.1: Rollback on failure (AC3.1)

See `docs/test-plans/2026-03-27-rollback-verification.md` for detailed steps.

- [ ] Failed deploy restores entire previous installation (binaries + config)
- [ ] Old version restarted
- [ ] Audit log records failure and rollback

### Test 5.2: Model download retry (AC3.2)

See `docs/test-plans/2026-03-27-rollback-verification.md` Step 2.

- [ ] Invalid model URL causes 3 retry attempts
- [ ] Exponential backoff visible (2s, 4s, 8s)
- [ ] Clear error after final failure
- [ ] Audit log records retry attempts

### Test 5.3: Process not running (AC3.4)

Ensure target process is not running, then deploy:

```powershell
Stop-Process -Name WhisperService -Force -ErrorAction SilentlyContinue
powershell -ExecutionPolicy Bypass -File deploy-app.ps1 -App whisper-service
```

- [ ] Output shows "not running" skip message
- [ ] Deploy completes successfully

---

## Part 6: CI Workflow Verification

### Test 6.1: CI trigger (AC1.1)

1. Merge whisper-service PR to `main`
2. Check GitHub Actions tab

- [ ] `Build and Release` workflow triggers on `windows-latest`
- [ ] Vulnerability scan job runs first
- [ ] Build + release job runs after scan passes
- [ ] Release created with 3 assets (zip, sha256, appsettings.default.json)

### Test 6.2: Vulnerable package blocks release (AC1.7)

1. Create test branch in whisper-service
2. Add a known-vulnerable NuGet package
3. Trigger workflow via `workflow_dispatch`

- [ ] Vulnerability scan job fails
- [ ] No release created
- [ ] Revert the change

---

## Results Summary

| Section | Tests | Pass | Fail | Notes |
|---------|-------|------|------|-------|
| Automated (Python) | 2 | | | AC1.5, AC1.6 |
| Automated (PowerShell) | 3 | | | AC2.6, AC3.3, AC4.3 |
| Bootstrap | 3 | | | AC4.1, AC4.2, AC4.3 |
| Whisper-Service | 5 | | | AC1.2-1.4, AC2.1-2.5 |
| SysTTS | 2 | | | AC5.2, AC5.3 |
| Error Recovery | 3 | | | AC3.1, AC3.2, AC3.4 |
| CI Workflow | 2 | | | AC1.1, AC1.7 |
| **Total** | **20** | | | |

**Tester:** _______________  **Date:** _______________
