# Windows App Deployment - End-to-End Bootstrap Test Procedure

Phase: Phase 3, Task 3
Date: 2026-03-27
Status: Manual Windows Execution Required

---

## Overview

This document describes the manual test procedure for Task 3 (End-to-end bootstrap test) from Phase 3. These tests verify:
- **AC4.1:** Double-clicking `.bat` file on desktop runs full deploy cycle with visible output
- **AC4.2:** `bootstrap-deploy.ps1` copies tooling to `%USERPROFILE%\tools\` and `.bat` to Desktop
- **AC4.3:** Bootstrap is idempotent — safe to re-run without duplicating files or breaking existing installs

## Prerequisites

- Windows 10/11 with PowerShell 5.0+ (or PowerShell Core)
- GitHub CLI (`gh`) installed via `winget install GitHub.cli`
- GitHub CLI authenticated via `gh auth login`
- Clone of claude-env repository at `C:\dev\claude-env` (or your preferred path)

## Test Procedure

### Step 1: Run Bootstrap on Windows

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
- "Setting up tools directory..." shows "Created" or "Already exists" (Green)
- "Copying deployment scripts..." shows three files copied:
  - `deploy-app.ps1` (Green)
  - `app-registry.json` (Green)
  - `Deploy-App.bat.template` (Green)
- "Creating desktop shortcuts..." section shows:
  - For each app in registry: "Created: Deploy <app-name>.bat" (Cyan)
  - Example: "Created: Deploy whisper-service.bat" (Cyan)
- "Shortcut creation summary" shows "Created: 1" (Green)
- "Bootstrap complete!" message (Green)
- Next steps listed

**Verification Checklist:**
- [ ] Output shows no errors (all Red-colored error messages would indicate failure)
- [ ] `%USERPROFILE%\tools\deploy-app.ps1` exists (verify by opening File Explorer and navigating)
- [ ] `%USERPROFILE%\tools\app-registry.json` exists
- [ ] `%USERPROFILE%\Desktop\Deploy whisper-service.bat` exists and has Windows `.bat` icon

### Step 2: Verify Idempotency

Run the bootstrap script a second time (same command as Step 1):

```powershell
powershell -ExecutionPolicy Bypass -File bootstrap-deploy.ps1
```

**Expected Output:**
- Bootstrap Setup header again
- Prerequisites check passes
- Tools directory shows "Already exists: $toolsDir" (Green)
- Files copied again (same as Step 1 — this is correct, as claude-env manages these)
- Desktop shortcuts section shows "Skipped (already exists): Deploy whisper-service.bat" (Yellow)
- "Shortcut creation summary" shows:
  - "Created: 0"
  - "Skipped: 1" (Yellow)
- No errors, script exits with success

**Verification Checklist:**
- [ ] No errors occur (exit code 0)
- [ ] Files are not duplicated in `%USERPROFILE%\tools\`
- [ ] Desktop `.bat` file is not duplicated
- [ ] Skipped message appears for existing `.bat` files (Yellow text)
- [ ] Output clearly indicates idempotency ("already exists", "skipped")

### Step 3: Verify .bat Runs Deploy

**Before running .bat:**
- Close any running instances of the application (whisper-service)
- Ensure you have internet connection (for GitHub releases download)

**Test Steps:**

1. Open File Explorer and navigate to Desktop
2. Right-click `Deploy whisper-service.bat`
3. Select "Open" (or double-click)
4. A new Command Prompt window should open with:
   - Title bar showing "Deploy whisper-service"
   - Banner with "========================================" and "Deploying whisper-service"
   - Output from PowerShell execution

**Expected Output (from the .bat file execution):**

```
========================================
  Deploying whisper-service
========================================

Deployment: whisper-service
  Repo: psford/whisper-service
  Install dir: <UserProfile>\Apps\WhisperService
Prerequisites OK
Downloading release artifacts...
[... detailed deployment output ...]
Deploy complete.

Press any key to continue . . .
```

**Verification Checklist:**
- [ ] Command Prompt window opens with correct title
- [ ] Banner displays "Deploying whisper-service"
- [ ] PowerShell execution is visible (deployment output appears)
- [ ] Exit code handling works: either "Deploy complete." (success) or "Deploy FAILED" (if download failed)
- [ ] `pause` command at end keeps window open for user to review
- [ ] Files appear in `%USERPROFILE%\Apps\WhisperService\` after successful deploy

## Test Result Documentation

After completing all three steps, record your results:

### Success Criteria

**All three tests pass if:**

1. ✓ Bootstrap script runs without errors and creates files in correct locations
2. ✓ Second bootstrap run is idempotent (no duplicates, shows "skipped" for existing files)
3. ✓ Double-clicking `.bat` file calls `deploy-app.ps1` with correct app name parameter
4. ✓ `.bat` file produces visible output with proper exit code handling

### Failure Modes and Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "gh CLI not found" error | GitHub CLI not installed | Run: `winget install GitHub.cli` |
| "gh CLI not authenticated" error | Not logged into GitHub | Run: `gh auth login` and follow prompts |
| Bootstrap runs but no `.bat` files created | `app-registry.json` empty or missing | Verify `app-registry.json` is in windows-deploy directory with valid JSON |
| `.bat` file shows "Deploy FAILED" | Release download failed or app config incorrect | Check internet connection, verify app exists in registry, check `deploy-app.ps1` logs |
| Command Prompt closes immediately after opening | Script error in `.bat` file | Check Command Prompt for "Press any key to continue" — the pause line should prevent instant closure |

## Notes for Windows Execution

- These tests **MUST be run on Windows** (not WSL2 or Linux)
- PowerShell version 5.0+ is recommended (Windows 10/11 have this by default)
- Administrator mode is optional but recommended for first-time setup
- File paths use Windows conventions (`%USERPROFILE%`, `C:\`, backslashes)
- The `-ExecutionPolicy Bypass` flag is required to run unsigned scripts

## Acceptance Criteria Mapping

| AC ID | Test Step(s) | Verification |
|-------|--------------|--------------|
| AC4.1 | Step 3 | Double-clicking `.bat` runs deploy with visible output and pause |
| AC4.2 | Step 1 | Bootstrap creates tools directory and `.bat` on Desktop |
| AC4.3 | Step 2 | Re-running bootstrap is safe, skips existing files, no duplicates |

---

**Status:** Ready for Windows execution
**Environment:** WSL2 - cannot execute (requires Windows)
**Files Implemented:**
- `infrastructure/windows-deploy/Deploy-App.bat.template` — .bat template with {APP_NAME} placeholder
- `infrastructure/windows-deploy/bootstrap-deploy.ps1` — Idempotent bootstrap script
- `infrastructure/windows-deploy/app-registry.json` — App configuration (existing)
- `infrastructure/windows-deploy/deploy-app.ps1` — Deployment script (existing)
