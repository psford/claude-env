# Windows App Deployment Pipeline - Phase 1: CI Workflow Template

**Goal:** Reusable GitHub Actions workflow that builds any .NET Windows app and publishes a versioned GitHub Release with checksum.

**Architecture:** Two-job CI pipeline on Windows runner — vulnerability scan gate, then build + publish + release creation. Template lives in claude-env, copied to each app repo with env var customization.

**Tech Stack:** GitHub Actions, .NET 8 SDK, PowerShell, softprops/action-gh-release

**Scope:** 5 phases from original design (phase 1 of 5)

**Codebase verified:** 2026-03-27

---

## Acceptance Criteria Coverage

This phase implements and tests:

### windows-app-deploy.AC1: CI builds and publishes versioned releases
- **windows-app-deploy.AC1.1 Success:** Push to `main` triggers Windows runner build, produces GitHub Release with zip artifact
- **windows-app-deploy.AC1.2 Success:** Release includes SHA256 checksum file matching the zip contents
- **windows-app-deploy.AC1.3 Success:** Release excludes `appsettings.json` and `models/` from the zip artifact
- **windows-app-deploy.AC1.4 Success:** Default `appsettings.json` attached as a separate release asset for first-time installs
- **windows-app-deploy.AC1.5 Success:** `dotnet list package --vulnerable` runs and fails the build if vulnerable packages detected
- **windows-app-deploy.AC1.6 Success:** All GitHub Actions pinned by commit SHA, not tag
- **windows-app-deploy.AC1.7 Failure:** Build with a known-vulnerable NuGet package fails CI before release creation

---

<!-- START_SUBCOMPONENT_A (tasks 1-2) -->

<!-- START_TASK_1 -->
### Task 1: Create CI workflow template in claude-env

**Verifies:** windows-app-deploy.AC1.1, AC1.2, AC1.3, AC1.4, AC1.5, AC1.6, AC1.7

**Files:**
- Create: `infrastructure/windows-deploy/build-release.yml`

**Step 1: Create the directory and workflow template**

Create `infrastructure/windows-deploy/build-release.yml` — a reusable workflow template that app repos copy. Parameterized via `env:` variables at the top that each repo customizes:

```yaml
name: Build and Release

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  APP_NAME: WhisperService          # Display name for release
  PROJECT_PATH: WhisperService/WhisperService.csproj
  APPSETTINGS_SOURCE: WhisperService/appsettings.json
  PUBLISH_DIR: publish
  DOTNET_VERSION: '8.0'

jobs:
  vulnerability-scan:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@de0fac2dfffc5ffc2c1a8cead8e7b8d24cf50dcf

      - uses: actions/setup-dotnet@c2fa09f4bde5ebb9d1777cf28262a3eb3db3ced7
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}

      - name: Check for vulnerable packages
        shell: pwsh
        run: |
          $output = dotnet list ${{ env.PROJECT_PATH }} package --vulnerable --include-transitive 2>&1
          Write-Output $output
          if ($output -match "has the following vulnerable packages") {
            Write-Error "Vulnerable NuGet packages detected. Fix before releasing."
            exit 1
          }

  build-and-release:
    needs: vulnerability-scan
    runs-on: windows-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@de0fac2dfffc5ffc2c1a8cead8e7b8d24cf50dcf

      - uses: actions/setup-dotnet@c2fa09f4bde5ebb9d1777cf28262a3eb3db3ced7
        with:
          dotnet-version: ${{ env.DOTNET_VERSION }}

      - name: Publish self-contained
        run: >
          dotnet publish ${{ env.PROJECT_PATH }}
          -c Release
          -r win-x64
          --self-contained true
          -p:PublishReadyToRun=true
          -o ${{ env.PUBLISH_DIR }}

      - name: Remove user-configurable files from publish
        shell: pwsh
        run: |
          $publishDir = "${{ env.PUBLISH_DIR }}"
          Remove-Item -Path "$publishDir/appsettings.json" -ErrorAction SilentlyContinue
          Remove-Item -Path "$publishDir/appsettings.Development.json" -ErrorAction SilentlyContinue
          Remove-Item -Path "$publishDir/models" -Recurse -ErrorAction SilentlyContinue

      - name: Save default appsettings as separate asset
        shell: pwsh
        run: |
          Copy-Item "${{ env.APPSETTINGS_SOURCE }}" "appsettings.default.json"

      - name: Create zip and checksum
        shell: pwsh
        run: |
          $zipName = "${{ env.APP_NAME }}-win-x64.zip"
          Compress-Archive -Path "${{ env.PUBLISH_DIR }}/*" -DestinationPath $zipName
          $hash = Get-FileHash -Path $zipName -Algorithm SHA256
          "$($hash.Hash.ToLower())  $zipName" | Out-File -FilePath "$zipName.sha256" -Encoding ASCII

      - name: Create GitHub Release
        uses: softprops/action-gh-release@153bb8e04406b158c6c84fc1615b65b24149a1fe
        with:
          tag_name: v1.0.${{ github.run_number }}
          name: ${{ env.APP_NAME }} v1.0.${{ github.run_number }}
          generate_release_notes: true
          files: |
            ${{ env.APP_NAME }}-win-x64.zip
            ${{ env.APP_NAME }}-win-x64.zip.sha256
            appsettings.default.json
```

**Step 2: Verify template is valid YAML**

Run: `python3 -c "import yaml; yaml.safe_load(open('infrastructure/windows-deploy/build-release.yml'))"`

Expected: No errors.

**Step 3: Commit**

```bash
git add infrastructure/windows-deploy/build-release.yml
git commit -m "feat: add CI workflow template for Windows app releases"
```
<!-- END_TASK_1 -->

<!-- START_TASK_2 -->
### Task 2: Install CI workflow in whisper-service repo

**Verifies:** windows-app-deploy.AC1.1 (end-to-end verification)

**Files:**
- Create: `/home/patrick/projects/whisper-service/.github/workflows/build-release.yml`

**Step 1: Copy and customize template for whisper-service**

```bash
mkdir -p /home/patrick/projects/whisper-service/.github/workflows
cp /home/patrick/projects/claude-env/infrastructure/windows-deploy/build-release.yml \
   /home/patrick/projects/whisper-service/.github/workflows/build-release.yml
```

The template already has correct values for whisper-service (`APP_NAME: WhisperService`, `PROJECT_PATH: WhisperService/WhisperService.csproj`). No edits needed for the first consumer.

**Step 2: Verify YAML is valid**

Run: `cd /home/patrick/projects/whisper-service && python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-release.yml'))"`

Expected: No errors.

**Step 3: Commit in whisper-service repo**

```bash
cd /home/patrick/projects/whisper-service
git add .github/workflows/build-release.yml
git commit -m "feat: add CI workflow for automated releases"
```

**Step 4: Verify CI triggers** (after push to main via PR)

After the workflow is on `main`, push triggers a build. Verify:
- GitHub Actions shows the workflow running on `windows-latest`
- Release is created with zip, checksum, and default appsettings
- Vulnerability scan job runs

**Verification:**
Run: Check GitHub Actions tab after merge to main
Expected: Build succeeds, release created with 3 assets (zip, sha256, appsettings.default.json)
<!-- END_TASK_2 -->

<!-- END_SUBCOMPONENT_A -->
