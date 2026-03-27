# Windows App Deployment - Rollback Verification Test Procedure

Phase: Phase 4, Task 4
Date: 2026-03-27
Status: Manual Windows Execution Required

---

## Overview

This document describes the manual test procedure for Task 4 (Rollback verification test) from Phase 4. These tests verify:
- **AC3.1:** Failed deploy at any step restores backup and restarts previous version
- **AC3.2:** Model download failure retries 3x with backoff, reports clear error

This is a three-step verification process that tests the rollback and error recovery behavior implemented in Phases 2, 3, and 4 of the deployment pipeline.

## Prerequisites

- Windows 10/11 with PowerShell 5.0+ (or PowerShell Core)
- GitHub CLI (`gh`) installed via `winget install GitHub.cli`
- GitHub CLI authenticated via `gh auth login`
- Clone of claude-env repository at `C:\dev\claude-env` (or your preferred path)
- Successful prior deployment of whisper-service (for rollback testing)
- `whisper-service` application currently running on target system (to verify backup/restore)
- Read/write access to `%USERPROFILE%\Apps\WhisperService\` directory
- Read/write access to `%USERPROFILE%\Apps\deploy-log.txt` (audit log)

## Test Procedure

### Step 1: Verify Rollback on Checksum Failure

This step verifies that **AC3.1** (failed deploy restores backup and restarts previous version) by simulating a tampered release artifact.

**Prerequisite Verification:**
1. Ensure `whisper-service` is currently running and deployed
2. Note the current version running: check in Task Manager or query `app-registry.json`
3. Verify `%USERPROFILE%\Apps\WhisperService\` directory exists with application files

**Test Steps:**

1. Open PowerShell and create a temporary test directory:
   ```powershell
   $tempDir = "$env:TEMP\deploy-test"
   if (Test-Path $tempDir) { Remove-Item -Path $tempDir -Recurse -Force }
   New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
   ```

2. Download the latest release artifacts from whisper-service:
   ```powershell
   cd $tempDir
   gh release download --pattern '*.zip' -R psford/whisper-service -D $tempDir
   gh release download --pattern '*.sha256' -R psford/whisper-service -D $tempDir
   ```

   **Expected:** Two files appear in `$tempDir`:
   - `WhisperService-win-x64.zip`
   - `WhisperService-win-x64.zip.sha256`

3. Tamper with the checksum file to simulate artifact corruption:
   ```powershell
   Set-Content -Path "$tempDir\WhisperService-win-x64.zip.sha256" -Value "0000000000000000000000000000000000000000000000000000000000000000  WhisperService-win-x64.zip"
   ```

4. Verify the checksum file was modified:
   ```powershell
   Get-Content "$tempDir\WhisperService-win-x64.zip.sha256"
   ```

   **Expected:** Output shows the fake checksum "0000000000000000000000000000000000000000000000000000000000000000"

5. Run the deploy script manually to trigger the checksum failure:
   ```powershell
   cd C:\dev\claude-env\infrastructure\windows-deploy
   powershell -ExecutionPolicy Bypass -File deploy-app.ps1 -App whisper-service -TempDir $tempDir
   ```

   **Note:** Adjust the command parameters to match the actual deploy-app.ps1 signature if different.

**Expected Output:**

- Script downloads or uses provided artifacts from `$tempDir`
- Checksum validation step extracts hash from `WhisperService-win-x64.zip.sha256`
- Script detects mismatch between calculated hash and fake hash
- Error message appears: "Checksum mismatch detected. Artifact may be tampered or corrupted."
- Script **does not extract or install** the tampered archive
- Script retrieves the backup of the previous version from `%USERPROFILE%\Apps\WhisperService\.backup\`
- Previous version files are restored to `%USERPROFILE%\Apps\WhisperService\`
- Application process is restarted with the previous version
- Audit log is updated with failure and rollback information

**Verification Checklist:**

- [ ] Script output shows "Checksum mismatch" error message
- [ ] Deploy process aborts without extracting the bad archive
- [ ] Backup directory `%USERPROFILE%\Apps\WhisperService\.backup\` exists and contains previous version
- [ ] Application files in `%USERPROFILE%\Apps\WhisperService\` are restored to previous version
- [ ] `whisper-service` process is running again after rollback
- [ ] Audit log (`%USERPROFILE%\Apps\deploy-log.txt`) contains entries showing:
  - Download started
  - Checksum verification failed
  - Rollback initiated
  - Backup restored
  - Process restarted with previous version
- [ ] Application functions correctly with the restored version
- [ ] No corrupted files remain in the install directory

---

### Step 2: Verify Model Download Retry on Failure

This step verifies that **AC3.2** (model download failure retries 3x with backoff) by simulating an invalid Hugging Face model URL.

**Prerequisite Verification:**
1. Verify `app-registry.json` exists at `%USERPROFILE%\tools\app-registry.json` (or `infrastructure\windows-deploy\app-registry.json`)
2. Check that it contains valid model entries with Hugging Face URLs
3. Ensure whisper-service is deployed and ready for update testing

**Test Steps:**

1. Locate and open `app-registry.json`:
   ```powershell
   $regPath = "$env:USERPROFILE\tools\app-registry.json"
   if (-not (Test-Path $regPath)) {
       $regPath = "C:\dev\claude-env\infrastructure\windows-deploy\app-registry.json"
   }
   notepad $regPath
   ```

2. Create a backup of the original configuration:
   ```powershell
   Copy-Item -Path $regPath -Destination "$regPath.backup"
   ```

3. Modify the registry to use an invalid Hugging Face URL for the model:
   - Find the section containing model URLs (typically a property like `"modelUrl"` or `"huggingface_repo"`)
   - Change it to an invalid/unreachable URL: `"https://huggingface.co/invalid/model-does-not-exist/resolve/main/model.bin"`
   - Save the file

4. Run a deploy to trigger model download with the invalid URL:
   ```powershell
   cd C:\dev\claude-env\infrastructure\windows-deploy
   powershell -ExecutionPolicy Bypass -File deploy-app.ps1 -App whisper-service
   ```

**Expected Output:**

- Binary deployment succeeds (whisper-service application is updated)
- Model download begins
- First attempt fails with network/404 error
- Script logs: "Model download attempt 1 of 3 failed. Retrying in 2 seconds..."
- Second attempt fails
- Script logs: "Model download attempt 2 of 3 failed. Retrying in 4 seconds..."
- Third attempt fails
- Script logs: "Model download attempt 3 of 3 failed. Retrying in 8 seconds..."
- After third failure, script reports clear error: "Model download failed after 3 attempts with exponential backoff. Check URL and network connectivity."
- Deploy completes with warning about missing model (application still runs with fallback)
- Audit log records each retry attempt and backoff intervals

**Verification Checklist:**

- [ ] Binary application update succeeds
- [ ] Model download attempts are logged with attempt numbers (1/3, 2/3, 3/3)
- [ ] Backoff intervals are correct (2s, 4s, 8s)
- [ ] Script waits the correct duration between retries (can observe in output timestamps)
- [ ] Clear error message appears after final failure
- [ ] Audit log (`%USERPROFILE%\Apps\deploy-log.txt`) contains entries showing:
  - "Model download failed: invalid URL"
  - "Retry attempt 1, backoff: 2s"
  - "Retry attempt 2, backoff: 4s"
  - "Retry attempt 3, backoff: 8s"
  - "Model download FAILED after 3 retries"
- [ ] Application remains functional with the updated binary (even without the model)
- [ ] No partial/corrupted model file is left in the install directory

---

### Step 3: Restore Valid Configuration

This step restores the application to a known-good state after testing.

**Test Steps:**

1. Restore the backup of `app-registry.json`:
   ```powershell
   $regPath = "$env:USERPROFILE\tools\app-registry.json"
   if (-not (Test-Path $regPath)) {
       $regPath = "C:\dev\claude-env\infrastructure\windows-deploy\app-registry.json"
   }
   Copy-Item -Path "$regPath.backup" -Destination $regPath -Force
   ```

2. Verify the configuration is restored:
   ```powershell
   Get-Content $regPath | ConvertFrom-Json | Format-Table -AutoSize
   ```

   **Expected:** Output shows the original app registry with valid Hugging Face URLs

3. Run a final deploy to restore the model with the correct URL:
   ```powershell
   cd C:\dev\claude-env\infrastructure\windows-deploy
   powershell -ExecutionPolicy Bypass -File deploy-app.ps1 -App whisper-service
   ```

   **Expected:** Model downloads successfully from the correct URL

4. Clean up test files:
   ```powershell
   Remove-Item -Path "$regPath.backup" -Force
   $tempDir = "$env:TEMP\deploy-test"
   if (Test-Path $tempDir) { Remove-Item -Path $tempDir -Recurse -Force }
   ```

**Verification Checklist:**

- [ ] Configuration file restored to original state
- [ ] Valid model URLs are in place
- [ ] Final deploy runs successfully
- [ ] Model downloads without errors
- [ ] Application functions with restored configuration
- [ ] Test artifacts are cleaned up

---

## Test Result Documentation

After completing all three steps, record your results:

### Success Criteria

**All three tests pass if:**

1. ✓ Checksum mismatch is detected and deploy aborts before extraction
2. ✓ Previous version is restored from backup automatically
3. ✓ Application process is restarted with the restored version
4. ✓ Audit log captures the failure and rollback sequence
5. ✓ Model download retries exactly 3 times with exponential backoff (2s, 4s, 8s)
6. ✓ Clear error message is reported after final retry failure
7. ✓ Audit log captures all retry attempts with timestamps and backoff intervals
8. ✓ Valid configuration is restored and application functions normally

### Failure Modes and Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Checksum mismatch" not reported | Script may not validate checksums | Verify deploy-app.ps1 includes `Get-FileHash` validation from Phase 2 |
| Rollback doesn't happen | Backup not created on first deploy | Ensure Phase 3 implementation created backup infrastructure |
| Application doesn't restart | Process termination/restart logic missing | Check deploy-app.ps1 for `Stop-Process` and service restart commands |
| Retry attempts not logged | Audit logging not implemented | Verify Phase 4 Task 3 (audit logging) was completed before this test |
| Model download doesn't retry | Retry logic not implemented | Verify Phase 2 or 3 includes model download retry mechanism |
| Invalid URL causes network timeout instead of 404 | Network connectivity issue | Check internet connection, verify URL is truly unreachable |
| Audit log not created | Log directory creation failed | Verify `%USERPROFILE%\Apps\` directory is writable |
| Audit log not updated | Write-AuditLog function not called | Confirm audit logging is integrated at all required steps |

---

## Notes for Windows Execution

- These tests **MUST be run on Windows** (not WSL2 or Linux)
- PowerShell version 5.0+ is required
- Administrator mode is recommended for stopping/starting processes and managing backups
- File paths use Windows conventions (`%USERPROFILE%`, `%TEMP%`, backslashes)
- The `-ExecutionPolicy Bypass` flag is required to run unsigned scripts
- Rollback testing should be performed on a non-production system first
- Model download testing requires internet connectivity
- Test can impact running whisper-service instances — schedule when downtime is acceptable

---

## Acceptance Criteria Mapping

| AC ID | Test Step(s) | Verification |
|-------|--------------|--------------|
| AC3.1 | Step 1 | Checksum mismatch triggers backup restore and process restart |
| AC3.2 | Step 2 | Model download fails after 3 retries with exponential backoff and clear error |
| AC3.3 | Steps 1-2 | Audit log captures all deploy actions with timestamps |

---

## Phase Dependencies

This test validates implementations from:
- **Phase 2, Task 2:** Checksum validation and extraction (foundation for Step 1)
- **Phase 3, Task 1-2:** Backup creation and process management (required for Step 1 rollback)
- **Phase 4, Task 1:** Release provenance check (context for deploy security)
- **Phase 4, Task 2:** Path validation (context for safe extraction)
- **Phase 4, Task 3:** Audit logging (verification mechanism for Steps 1-2)

---

**Status:** Ready for Windows execution
**Environment:** WSL2 - cannot execute (requires Windows)
**Prerequisites:** Phases 2, 3, and 4 implementation complete; whisper-service previously deployed successfully
