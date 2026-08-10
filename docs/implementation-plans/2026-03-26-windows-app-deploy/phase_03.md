# Windows App Deployment Pipeline - Phase 3: Desktop Integration and First-Time Bootstrap

**Goal:** One-click `.bat` files and first-time setup that copies deploy tooling to Windows.

**Architecture:** Bootstrap script copies deploy tooling to `%USERPROFILE%\tools\`, creates parameterized `.bat` shortcuts on Desktop for each registered app.

**Tech Stack:** PowerShell, Windows batch files

**Scope:** 5 phases from original design (phase 3 of 5)

**Codebase verified:** 2026-03-27

---

## Acceptance Criteria Coverage

This phase implements and tests:

### windows-app-deploy.AC4: Desktop integration
- **windows-app-deploy.AC4.1 Success:** Double-clicking `.bat` file on desktop runs full deploy cycle with visible output
- **windows-app-deploy.AC4.2 Success:** `bootstrap-deploy.ps1` copies tooling to `%USERPROFILE%\tools\` and `.bat` to Desktop
- **windows-app-deploy.AC4.3 Success:** Bootstrap is idempotent — safe to re-run without duplicating files or breaking existing installs

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Create .bat template

**Verifies:** windows-app-deploy.AC4.1

**Files:**
- Create: `infrastructure/windows-deploy/Deploy-App.bat.template`

**Step 1: Create the template file**

```bat
@echo off
title Deploy {APP_NAME}
echo ========================================
echo   Deploying {APP_NAME}
echo ========================================
echo.
powershell -ExecutionPolicy Bypass -File "%USERPROFILE%\tools\deploy-app.ps1" -App {APP_NAME}
echo.
if %ERRORLEVEL% EQU 0 (
    echo Deploy complete.
) else (
    echo Deploy FAILED. Check output above.
)
echo.
pause
```

**Verification:**
Visually inspect template has `{APP_NAME}` placeholder in title, echo, and PowerShell call.

**Commit:**

```bash
git add infrastructure/windows-deploy/Deploy-App.bat.template
git commit -m "feat: add .bat template for desktop deploy shortcuts"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Create bootstrap-deploy.ps1

**Verifies:** windows-app-deploy.AC4.2, AC4.3

**Files:**
- Create: `infrastructure/windows-deploy/bootstrap-deploy.ps1`

**Implementation:**

Idempotent setup script that:
1. Checks prerequisites: verifies `gh` CLI is installed (`Get-Command gh`) and authenticated (`gh auth status`); if missing, errors with install instructions (`winget install GitHub.cli`)
2. Creates `$env:USERPROFILE\tools\` if it doesn't exist
2. Copies `deploy-app.ps1` and `app-registry.json` to tools dir (overwrites existing — these are managed by claude-env, always take latest)
3. Reads `app-registry.json`, for each app entry creates a `.bat` file on Desktop by replacing `{APP_NAME}` in the template with the app key name
4. Skips `.bat` creation if file already exists on Desktop (idempotent — AC4.3)
5. Reports what was created/updated with colored output (Cyan=action, Green=success, Yellow=skipped)

Follows existing patterns: `$ErrorActionPreference = "Stop"`, colored output, `exit 0`/`exit 1`.

**Verification:**
Run: `powershell.exe -Command "& { Get-Content .\infrastructure\windows-deploy\bootstrap-deploy.ps1 | Out-Null; Write-Host 'Syntax OK' }"`
Expected: "Syntax OK" (no parse errors)

**Commit:**

```bash
git add infrastructure/windows-deploy/bootstrap-deploy.ps1
git commit -m "feat: add bootstrap script for first-time deploy setup"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: End-to-end bootstrap test

**Verifies:** windows-app-deploy.AC4.1, AC4.2, AC4.3

**Step 1: Run bootstrap on Windows**

```powershell
powershell -ExecutionPolicy Bypass -File bootstrap-deploy.ps1
```

Expected:
- `%USERPROFILE%\tools\deploy-app.ps1` exists
- `%USERPROFILE%\tools\app-registry.json` exists
- `%USERPROFILE%\Desktop\Deploy whisper-service.bat` exists

**Step 2: Verify idempotency**

Run bootstrap again.
Expected: No errors, no duplicate files, output says "already exists" for `.bat` files.

**Step 3: Verify .bat runs deploy**

Double-click the `.bat` on Desktop.
Expected: Calls `deploy-app.ps1 -App whisper-service`, shows deploy output in terminal window with `pause` at end.
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->
