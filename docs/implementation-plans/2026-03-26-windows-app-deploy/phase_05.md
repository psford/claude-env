# Windows App Deployment Pipeline - Phase 5: SysTTS Onboarding

**Goal:** Validate the pipeline is truly general-purpose by onboarding a second app.

**Architecture:** Add SysTTS to app registry with multi-model configuration (Piper voices + espeak-ng-data), install CI workflow from template. No deploy script changes needed — array model support built in Phase 2.

**Tech Stack:** PowerShell, GitHub Actions, gh CLI, tar

**Scope:** 5 phases from original design (phase 5 of 5)

**Codebase verified:** 2026-03-27

---

## Acceptance Criteria Coverage

This phase implements and tests:

### windows-app-deploy.AC5: General-purpose (multi-app)
- **windows-app-deploy.AC5.1 Success:** Adding a new app requires only a registry entry, CI workflow from template, and `.bat` file
- **windows-app-deploy.AC5.2 Success:** SysTTS deploys via the same pipeline as whisper-service with no script modifications
- **windows-app-deploy.AC5.3 Success:** Each app's config and models are isolated in separate install directories

---

<!-- START_SUBCOMPONENT_A (tasks 1-3) -->

<!-- START_TASK_1 -->
### Task 1: Add SysTTS entry to app-registry.json

**Verifies:** windows-app-deploy.AC5.1, AC5.3

**Files:**
- Modify: `infrastructure/windows-deploy/app-registry.json`

**Implementation:**

Add SysTTS entry alongside whisper-service. SysTTS has two model sources (Piper voice ONNX + espeak-ng-data), requiring array format for models:

```json
{
  "whisper-service": { "..." : "existing entry unchanged" },
  "systts": {
    "repo": "psford/SysTTS",
    "processName": "SysTTS",
    "installDir": "SysTTS",
    "startupShortcutName": "SysTTS",
    "appsettingsSourcePath": "src/SysTTS/appsettings.json",
    "models": [
      {
        "source": "huggingface",
        "baseUrl": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium",
        "files": ["en_US-amy-medium.onnx", "en_US-amy-medium.onnx.json"],
        "targetDir": "voices"
      },
      {
        "source": "github-release",
        "repo": "k2-fsa/sherpa-onnx",
        "tag": "tts-models",
        "file": "espeak-ng-data.tar.bz2",
        "targetDir": ".",
        "extract": true
      }
    ]
  }
}
```

The deploy script already handles both object format (whisper-service) and array format (SysTTS) — this was built into Phase 2.

**Verification:**
Run: `python3 -c "import json; d=json.load(open('infrastructure/windows-deploy/app-registry.json')); assert 'systts' in d; print('OK')"`
Expected: "OK"

**Commit:**

```bash
git add infrastructure/windows-deploy/app-registry.json
git commit -m "feat: add SysTTS to app registry"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Install CI workflow in SysTTS repo

**Verifies:** windows-app-deploy.AC5.2

**Files:**
- Create: `/home/patrick/projects/SysTTS/.github/workflows/build-release.yml`

**Implementation:**

Copy template from claude-env and customize the `env:` block for SysTTS:

```yaml
env:
  APP_NAME: SysTTS
  PROJECT_PATH: src/SysTTS/SysTTS.csproj
  APPSETTINGS_SOURCE: src/SysTTS/appsettings.json
  PUBLISH_DIR: publish
  DOTNET_VERSION: '8.0'
```

No other changes needed — the template already uses `${{ env.APPSETTINGS_SOURCE }}` in the default appsettings step.

**Verification:**
Run: `cd /home/patrick/projects/SysTTS && python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-release.yml'))"`
Expected: No errors.

**Commit (in SysTTS repo):**

```bash
cd /home/patrick/projects/SysTTS
git add .github/workflows/build-release.yml
git commit -m "feat: add CI workflow for automated releases"
```
<!-- END_TASK_2 -->

<!-- START_TASK_3 -->
### Task 3: End-to-end SysTTS deploy test

**Verifies:** windows-app-deploy.AC5.2, AC5.3

**Step 1: Run bootstrap**

Re-run `bootstrap-deploy.ps1` on Windows.
Expected: Creates `Deploy systts.bat` on Desktop alongside existing `Deploy whisper-service.bat`.

**Step 2: Deploy SysTTS**

Double-click `Deploy systts.bat`.
Expected: Downloads latest SysTTS release, installs to `%USERPROFILE%\Apps\SysTTS\`, downloads Piper models and espeak-ng-data, starts app.

**Step 3: Verify isolation**

Confirm:
- `%USERPROFILE%\Apps\WhisperService\` has whisper-service binaries + config + models
- `%USERPROFILE%\Apps\SysTTS\` has SysTTS binaries + config + models
- No cross-contamination between directories
- Each app runs independently
<!-- END_TASK_3 -->

<!-- END_SUBCOMPONENT_A -->
