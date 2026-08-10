# Windows App Deployment Pipeline - Phase 4: Security Hardening and Audit Logging

**Goal:** Defense-in-depth verification and deploy audit trail.

**Architecture:** Enhance deploy-app.ps1 with release provenance checking, path containment validation, and timestamped audit logging. Verify rollback behavior under failure conditions.

**Tech Stack:** PowerShell, gh CLI API, Get-FileHash

**Scope:** 5 phases from original design (phase 4 of 5)

**Codebase verified:** 2026-03-27

---

## Acceptance Criteria Coverage

This phase implements and tests:

### windows-app-deploy.AC2: Deploy script installs and updates apps
- **windows-app-deploy.AC2.5 Failure:** Deploy rejects artifact with mismatched checksum (tampered zip) — *implemented in Phase 2, verified here*
- **windows-app-deploy.AC2.6 Failure:** Deploy refuses to write outside the app's install directory

### windows-app-deploy.AC3: Rollback and error recovery
- **windows-app-deploy.AC3.1 Success:** Failed deploy at any step restores backup and restarts previous version
- **windows-app-deploy.AC3.2 Success:** Model download failure (network error) retries 3x with backoff, reports clear error
- **windows-app-deploy.AC3.3 Success:** All deploy actions logged to timestamped audit file

---

<!-- START_TASK_1 -->
### Task 1: Add release provenance check to deploy-app.ps1

**Verifies:** windows-app-deploy.AC2.5

**Files:**
- Modify: `infrastructure/windows-deploy/deploy-app.ps1`

**Implementation:**

After downloading the release, before extracting, query release metadata via `gh api`:

```powershell
$releaseInfo = gh api "repos/$repo/releases/latest" | ConvertFrom-Json
if ($releaseInfo.author.login -ne "github-actions[bot]") {
    Write-Error "Release was not created by GitHub Actions. Refusing to deploy."
    exit 1
}
```

This ensures only CI-produced releases are deployed, not manually uploaded artifacts.

**Verification:**
Run deploy against a repo with a CI-created release — should pass.
Manually create a release and attempt deploy — should be rejected.

**Commit:** `feat: add release provenance check to deploy script`
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Add path validation to deploy-app.ps1

**Verifies:** windows-app-deploy.AC2.6

**Files:**
- Modify: `infrastructure/windows-deploy/deploy-app.ps1`

**Implementation:**

Add path containment validation function:

```powershell
function Assert-PathWithinInstallDir {
    param([string]$Path, [string]$InstallDir)
    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    $resolvedInstall = [System.IO.Path]::GetFullPath($InstallDir)
    if (-not $resolvedPath.StartsWith($resolvedInstall)) {
        throw "Path '$resolvedPath' is outside install directory '$resolvedInstall'. Refusing to write."
    }
}
```

Call before `Expand-Archive` and before any `Copy-Item` to the install directory.

**Verification:**
Test with a path containing `..` that escapes install directory — should throw error and abort.

**Commit:** `feat: add path validation to prevent writes outside install dir`
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: Add audit logging to deploy-app.ps1

**Verifies:** windows-app-deploy.AC3.3

**Files:**
- Modify: `infrastructure/windows-deploy/deploy-app.ps1`

**Implementation:**

Add audit logging function:

```powershell
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
```

Call at each major step:
- Download started (version/tag)
- Checksum verified (hash value)
- Provenance verified (release author)
- Process stopped (or "not running")
- Backup created (path)
- Archive extracted
- Config restored (or "first install — defaults applied")
- Models checked (found/downloaded/failed)
- Process started (PID)
- Deploy complete (or "FAILED: <error>")

**Verification:**
Run a deploy, then inspect `%USERPROFILE%\Apps\deploy-log.txt`.
Expected: Timestamped entries for each step with app name.

**Commit:** `feat: add audit logging to deploy script`
<!-- END_TASK_3 -->

<!-- START_TASK_4 -->
### Task 4: Rollback verification test

**Verifies:** windows-app-deploy.AC3.1, AC3.2

**Step 1: Verify rollback on checksum failure**

After a successful deploy, test checksum rejection by modifying the `.sha256` file contents:

```powershell
# Download release assets to a temp dir
$tempDir = "$env:TEMP\deploy-test"
gh release download --pattern '*.zip' -R psford/whisper-service -D $tempDir
gh release download --pattern '*.sha256' -R psford/whisper-service -D $tempDir

# Tamper with the checksum file
Set-Content -Path "$tempDir\WhisperService-win-x64.zip.sha256" -Value "0000000000000000  WhisperService-win-x64.zip"

# Run deploy — should detect mismatch and abort
```

Expected:
- Deploy reports checksum mismatch
- Previous version is restored from backup
- App is restarted with previous version
- Audit log records the failure and rollback

**Step 2: Verify model download retry**

Configure `app-registry.json` temporarily with an invalid Hugging Face URL. Run deploy.

Expected:
- Deploy succeeds for binary update
- Model download fails after 3 retries (2s, 4s, 8s backoff) with clear error message
- Audit log records each retry attempt and final failure

**Step 3: Restore valid configuration**

Reset `app-registry.json` to correct URLs after testing.
<!-- END_TASK_4 -->
