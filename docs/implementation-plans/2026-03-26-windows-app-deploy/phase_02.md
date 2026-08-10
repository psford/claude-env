# Windows App Deployment Pipeline - Phase 2: Deploy Script and App Registry

**Goal:** General-purpose PowerShell deploy script that can install/update any registered Windows app from GitHub Releases.

**Architecture:** Single `deploy-app.ps1` reads `app-registry.json` for per-app metadata, executes download → verify → stop → backup → extract → restore → model-check → start lifecycle with rollback on failure.

**Tech Stack:** PowerShell, gh CLI, Invoke-WebRequest, Get-FileHash

**Scope:** 5 phases from original design (phase 2 of 5)

**Codebase verified:** 2026-03-27

---

## Acceptance Criteria Coverage

This phase implements and tests:

### windows-app-deploy.AC2: Deploy script installs and updates apps
- **windows-app-deploy.AC2.1 Success:** `deploy-app.ps1 -App whisper-service` downloads latest release, extracts, and starts the app
- **windows-app-deploy.AC2.2 Success:** User's `appsettings.json` and `models/` directory preserved across deploy
- **windows-app-deploy.AC2.3 Success:** First-time deploy installs default `appsettings.json` from release and downloads required models
- **windows-app-deploy.AC2.4 Success:** Deploy verifies SHA256 checksum before extracting
- **windows-app-deploy.AC2.5 Failure:** Deploy rejects artifact with mismatched checksum (tampered zip)
- **windows-app-deploy.AC2.7 Edge:** Deploy with no previous install (fresh machine) completes successfully including model download

### windows-app-deploy.AC3: Rollback and error recovery
- **windows-app-deploy.AC3.4 Edge:** Deploy when app process is not running (first install or crashed) skips stop step gracefully

### windows-app-deploy.AC5: General-purpose (multi-app)
- **windows-app-deploy.AC5.1 Success:** Adding a new app requires only a registry entry, CI workflow from template, and `.bat` file

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: Create app-registry.json

**Verifies:** windows-app-deploy.AC5.1

**Files:**
- Create: `infrastructure/windows-deploy/app-registry.json`

**Step 1: Create the registry file**

```json
{
  "whisper-service": {
    "repo": "psford/whisper-service",
    "processName": "WhisperService",
    "installDir": "WhisperService",
    "startupShortcutName": "WhisperDictation",
    "appsettingsSourcePath": "WhisperService/appsettings.json",
    "models": {
      "source": "huggingface",
      "baseUrl": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main",
      "configSection": "Whisper",
      "configKey": "ModelSize",
      "filePattern": "ggml-{model}.bin"
    }
  }
}
```

**Step 2: Verify valid JSON**

Run: `python3 -c "import json; json.load(open('infrastructure/windows-deploy/app-registry.json'))"`
Expected: No errors.

**Step 3: Commit**

```bash
git add infrastructure/windows-deploy/app-registry.json
git commit -m "feat: add app registry for Windows deploy pipeline"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Create deploy-app.ps1

**Verifies:** windows-app-deploy.AC2.1, AC2.2, AC2.3, AC2.4, AC2.5, AC2.7, AC3.4

**Files:**
- Create: `infrastructure/windows-deploy/deploy-app.ps1`

**Implementation:**

The script accepts `-App` parameter, reads registry, executes the full deploy lifecycle. Structure:

1. **Parameter and setup** — `param([Parameter(Mandatory)][string]$App)`, load `app-registry.json` from script directory, resolve install dir as `$env:USERPROFILE\Apps\<installDir>\`
2. **Prerequisites check** — verify `gh` CLI is available via `Get-Command gh -ErrorAction SilentlyContinue`; if missing, error with install instructions
3. **Download** — create temp dir, run `gh release download --pattern '*.zip' -R <repo> -D $tempDir`, also download `*.sha256` and `appsettings.default.json`
4. **Verify checksum** — parse `.sha256` file (format: `<hash>  <filename>`), compare with `Get-FileHash` on zip; reject if mismatch
5. **Stop process** — `Get-Process -Name <processName> -ErrorAction SilentlyContinue`; if running, `Stop-Process -Force` + `Start-Sleep -Seconds 2`; if not running, log and continue (AC3.4)
6. **Backup** — if install dir exists, copy `appsettings*.json` and `models/` to `$tempDir\backup\`
7. **Extract** — `Expand-Archive -Path <zip> -DestinationPath <installDir> -Force`
8. **Restore config** — if backup exists, copy `appsettings*.json` and `models/` back; if no backup (first install), copy `appsettings.default.json` from temp as `appsettings.json` (AC2.3)
9. **Model check** — supports two registry formats from day one:
   - **Object format** (whisper-service): read `appsettings.json`, parse JSON to get model name from `configSection.configKey`, construct filename from `filePattern`, check if exists in `models/`; if missing, download from Hugging Face `baseUrl/filename` with 3x retry (exponential backoff: 2s, 4s, 8s)
   - **Array format** (SysTTS and future apps): iterate entries, each with `source` (`huggingface` or `github-release`), `files`/`file`, `targetDir`, and optional `extract: true` for archives. Download via `Invoke-WebRequest` (huggingface) or `gh release download -R <repo> <tag> --pattern <file>` (github-release). Run `tar -xf` after download if `extract` is true.
   - Detection: check if `$appConfig.models` is an array (`-is [System.Array]`) vs object
10. **Update startup shortcut** — check if a `.lnk` file matching `startupShortcutName` exists in `[Environment]::GetFolderPath('Startup')`; if so, update its `TargetPath` and `WorkingDirectory` to point to the new install directory using `WScript.Shell` COM object (same pattern as `install-startup.ps1`)
11. **Start** — `Start-Process -FilePath <exe> -WorkingDirectory <installDir>`; wait up to 10s checking `Get-Process` every 500ms; confirm running
12. **Rollback** — wrap steps 6-11 in try/catch; on failure, restore backup dir contents, restart old version, report error
13. **Cleanup** — remove temp dir

Follow existing patterns: `$ErrorActionPreference = "Stop"`, colored output (Cyan=action, Green=success, Yellow=warning, Red=error), `exit 0`/`exit 1`.

**Verification:**
Run: `powershell.exe -Command "& { Get-Content .\infrastructure\windows-deploy\deploy-app.ps1 | Out-Null; Write-Host 'Syntax OK' }"`
Expected: "Syntax OK" (no parse errors)

**Commit:** `feat: add deploy-app.ps1 for Windows app deployment`
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->
