# Windows App Deployment - SysTTS End-to-End Deploy Test Procedure

Phase: Phase 5, Task 3
Date: 2026-03-27
Status: Manual Windows Execution Required

---

## Overview

This document describes the manual test procedure for Task 3 (End-to-end SysTTS deploy test) from Phase 5. These tests verify:
- **AC5.2:** SysTTS deploys via the same pipeline as whisper-service with no script modifications
- **AC5.3:** Each app's config and models are isolated in separate install directories

## Prerequisites

- Windows 10/11 with PowerShell 5.0+ (or PowerShell Core)
- GitHub CLI (`gh`) installed via `winget install GitHub.cli`
- GitHub CLI authenticated via `gh auth login`
- Clone of claude-env repository at `C:\dev\claude-env` (or your preferred path)
- Previous successful completion of Phase 3 (whisper-service bootstrap and deploy) with Desktop shortcuts already created
- SysTTS GitHub Actions CI workflow must be merged (pushed) to psford/SysTTS main branch

## Test Procedure

### Step 1: Re-run Bootstrap on Windows

Open PowerShell (as Administrator recommended) and run:

```powershell
cd C:\dev\claude-env\infrastructure\windows-deploy
powershell -ExecutionPolicy Bypass -File bootstrap-deploy.ps1
```

**Expected Output:**
- Bootstrap Deploy Setup header with colored Cyan text
- "Script location:" shows the windows-deploy directory
- "Target paths:" shows `%USERPROFILE%\tools` and Desktop path
- "Checking prerequisites..." section completes with "Prerequisites OK" (Green)
- "Setting up tools directory..." shows "Already exists" (Green) — from Phase 3
- "Copying deployment scripts..." shows three files updated:
  - `deploy-app.ps1` (Green) — now handles both single-model (whisper-service) and multi-model (SysTTS) configurations
  - `app-registry.json` (Green) — **NOW INCLUDES systts ENTRY**
  - `Deploy-App.bat.template` (Green)
- "Creating desktop shortcuts..." section shows:
  - "Skipped (already exists): Deploy whisper-service.bat" (Yellow)
  - **"Created: Deploy systts.bat" (Cyan)** — NEW in Phase 5
- "Shortcut creation summary" shows:
  - "Created: 1" (Green) — the new SysTTS shortcut
  - "Skipped: 1" (Yellow) — the existing whisper-service shortcut
- "Bootstrap complete!" message (Green)

**Verification Checklist:**
- [ ] Output shows no errors (all Red-colored error messages would indicate failure)
- [ ] `%USERPROFILE%\Desktop\Deploy whisper-service.bat` still exists (unchanged from Phase 3)
- [ ] `%USERPROFILE%\Desktop\Deploy systts.bat` **NOW EXISTS** with Windows `.bat` icon
- [ ] Both `.bat` files are visible side-by-side on Desktop

### Step 2: Deploy SysTTS

**Before running .bat:**
- Close any running instances of SysTTS (if previously running)
- Ensure you have internet connection (for GitHub releases download and model downloads)
- Estimated download time: 5-10 minutes (includes Piper voice models + espeak-ng-data)

**Test Steps:**

1. Open File Explorer and navigate to Desktop
2. Right-click `Deploy systts.bat`
3. Select "Open" (or double-click)
4. A new Command Prompt window should open with:
   - Title bar showing "Deploy systts"
   - Banner with "========================================" and "Deploying systts"
   - Output from PowerShell execution

**Expected Output (from the .bat file execution):**

```
========================================
  Deploying systts
========================================

Deployment: systts
  Repo: psford/SysTTS
  Install dir: <UserProfile>\Apps\SysTTS
Prerequisites OK
Downloading release artifacts...
  Downloaded: SysTTS-win-x64.zip (SHA256 verification: OK)
Extracting to install directory...
Downloading models...
  [Piper voice models] Downloading en_US-amy-medium.onnx...
  [Piper voice models] Downloading en_US-amy-medium.onnx.json...
  [Piper voice models] Downloaded to voices\
  [espeak-ng-data] Downloading espeak-ng-data.tar.bz2...
  [espeak-ng-data] Extracting to app directory...
Updating appsettings...
  Created: appsettings.json
Starting application...
SysTTS is running.

Deploy complete.

Press any key to continue . . .
```

**Verification Checklist:**
- [ ] Command Prompt window opens with correct title "Deploy systts"
- [ ] Banner displays "Deploying systts"
- [ ] PowerShell execution is visible (deployment output appears)
- [ ] Both model sources download successfully:
  - [ ] Piper voice ONNX files appear in output
  - [ ] espeak-ng-data download and extraction appears in output
- [ ] Exit code handling works: "Deploy complete." (success) or "Deploy FAILED" (if download failed)
- [ ] `pause` command at end keeps window open for user to review
- [ ] Files appear in `%USERPROFILE%\Apps\SysTTS\` after successful deploy

### Step 3: Verify Isolation

**Test Steps:**

1. Open File Explorer and navigate to `%USERPROFILE%\Apps\`
2. Verify both directories exist side-by-side:
   - `WhisperService\` (from Phase 3)
   - `SysTTS\` (from Phase 5)

3. Inspect `%USERPROFILE%\Apps\WhisperService\`:
   - Should contain: WhisperService binaries, `appsettings.json`, `models/` directory (with Whisper models)
   - Should NOT contain: any SysTTS files, voices/, espeak-ng-data

4. Inspect `%USERPROFILE%\Apps\SysTTS\`:
   - Should contain: SysTTS binaries, `appsettings.json`, `voices/` directory (with Piper voice files), espeak-ng-data
   - Should NOT contain: any WhisperService files, Whisper models

5. Start both applications:
   - Open `%USERPROFILE%\Apps\WhisperService\WhisperService.exe` (should run independently)
   - Open `%USERPROFILE%\Apps\SysTTS\SysTTS.exe` (should run independently)
   - Both should run without conflicts or file access issues

**Verification Checklist:**
- [ ] Both `WhisperService\` and `SysTTS\` directories exist in `%USERPROFILE%\Apps\`
- [ ] WhisperService directory contains only whisper-service-related files
- [ ] SysTTS directory contains only SysTTS-related files
- [ ] No cross-contamination observed (files from one app in the other app's directory)
- [ ] WhisperService can start and run independently
- [ ] SysTTS can start and run independently
- [ ] Both applications can run simultaneously without conflicts

## Test Result Documentation

After completing all three steps, record your results:

### Success Criteria

**All three tests pass if:**

1. ✓ Bootstrap script re-runs, creates `Deploy systts.bat` on Desktop alongside existing `Deploy whisper-service.bat`
2. ✓ Double-clicking `Deploy systts.bat` runs full deploy cycle with visible model downloads
3. ✓ Both Piper voice models and espeak-ng-data download successfully
4. ✓ SysTTS installs to `%USERPROFILE%\Apps\SysTTS\` with complete directory structure
5. ✓ WhisperService and SysTTS directories are completely isolated (no cross-contamination)
6. ✓ Both applications can run independently and simultaneously

### Failure Modes and Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Deploy systts.bat not created" | SysTTS entry missing from app-registry.json in claude-env | Verify Phase 5, Task 1 completed — app-registry.json should have `systts` entry |
| "SysTTS GitHub release not found" | SysTTS CI workflow not yet triggered on main branch | Manually trigger GitHub Actions on SysTTS main branch: push a commit or use "Run workflow" button |
| "Model download failed" | Internet connection issues or incorrect model URLs in app-registry.json | Check internet connection, verify Piper and espeak-ng-data URLs are correct |
| "SysTTS fails to start after deploy" | Appsettings.json missing or corrupt | Check `%USERPROFILE%\Apps\SysTTS\appsettings.json` exists and is valid |
| "Files appear in wrong directory" | Deploy script logic error | Check `deploy-app.ps1` in `%USERPROFILE%\tools\` — verify it correctly handles array-format models |
| "Both apps running causes conflicts" | Resource contention or port conflicts | Check that both apps use different ports in their respective `appsettings.json` files |

## Notes for Windows Execution

- These tests **MUST be run on Windows** (not WSL2 or Linux)
- PowerShell version 5.0+ is recommended (Windows 10/11 have this by default)
- Administrator mode is optional but recommended for first-time setup
- File paths use Windows conventions (`%USERPROFILE%`, `C:\`, backslashes)
- The `-ExecutionPolicy Bypass` flag is required to run unsigned scripts
- Model downloads may take several minutes depending on internet speed

## Acceptance Criteria Mapping

| AC ID | Test Step(s) | Verification |
|-------|--------------|--------------|
| AC5.2 | Steps 1, 2 | Bootstrap creates SysTTS shortcut, deploy script handles array-format models correctly |
| AC5.3 | Step 3 | SysTTS and WhisperService directories isolated, each app runs independently |

---

**Status:** Ready for Windows execution
**Environment:** WSL2 - cannot execute (requires Windows)
**Files Implemented:**
- `infrastructure/windows-deploy/app-registry.json` — App configuration with SysTTS entry
- `infrastructure/windows-deploy/bootstrap-deploy.ps1` — Bootstrap script (already exists, reused)
- `infrastructure/windows-deploy/deploy-app.ps1` — Deployment script with array model support (already exists)
- `/home/patrick/projects/SysTTS/.github/workflows/build-release.yml` — CI workflow in SysTTS repo
