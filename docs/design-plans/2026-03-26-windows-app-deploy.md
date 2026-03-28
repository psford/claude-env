# Windows Application Deployment Pipeline Design

## Summary

This document designs a general-purpose deployment pipeline for Windows desktop applications built in the WSL2 Linux sandbox. Because the target apps (whisper-service, SysTTS) run natively on Windows but are developed in WSL2, they cannot use the standard web-app deployment model. Instead, the pipeline uses GitHub Actions with a Windows runner to compile and publish versioned releases, and a PowerShell script on the local Windows machine to pull and install those releases with a double-click. The design covers both the build side (CI workflow template, checksum generation, vulnerability scanning) and the install side (download, verify, stop, backup, extract, restore, start, rollback).

The approach is intentionally general-purpose: a single `deploy-app.ps1` script serves all apps by reading a central `app-registry.json` that maps app names to their GitHub repo, process name, install directory, and model download configuration. Adding a new app requires only a registry entry and a CI workflow copied from the template — no changes to shared scripts. Security is layered throughout: dependency vulnerability scanning blocks releases with known-vulnerable NuGet packages, SHA256 checksums verify every artifact before extraction, path validation prevents writes outside the install directory, and automatic rollback restores the previous working version on any failure.

## Definition of Done

A general-purpose deployment pipeline for Windows desktop applications developed in the WSL2 sandbox. Code changes made in WSL trigger CI builds on GitHub Actions (Windows runner), producing versioned release artifacts. A single `.bat` file on the Windows desktop downloads the latest release, preserves user configuration and model files, and restarts the application. The pipeline covers whisper-service, SysTTS, and any future Windows utility apps. Security is layered: pinned CI actions, locked dependencies, vulnerability scanning, checksum-verified artifacts, and rollback on failure.

## Acceptance Criteria

### windows-app-deploy.AC1: CI builds and publishes versioned releases
- **windows-app-deploy.AC1.1 Success:** Push to `main` triggers Windows runner build, produces GitHub Release with zip artifact
- **windows-app-deploy.AC1.2 Success:** Release includes SHA256 checksum file matching the zip contents
- **windows-app-deploy.AC1.3 Success:** Release excludes `appsettings.json` and `models/` from the zip artifact
- **windows-app-deploy.AC1.4 Success:** Default `appsettings.json` attached as a separate release asset for first-time installs
- **windows-app-deploy.AC1.5 Success:** `dotnet list package --vulnerable` runs and fails the build if vulnerable packages detected
- **windows-app-deploy.AC1.6 Success:** All GitHub Actions pinned by commit SHA, not tag
- **windows-app-deploy.AC1.7 Failure:** Build with a known-vulnerable NuGet package fails CI before release creation

### windows-app-deploy.AC2: Deploy script installs and updates apps
- **windows-app-deploy.AC2.1 Success:** `deploy-app.ps1 -App whisper-service` downloads latest release, extracts, and starts the app
- **windows-app-deploy.AC2.2 Success:** User's `appsettings.json` and `models/` directory preserved across deploy
- **windows-app-deploy.AC2.3 Success:** First-time deploy installs default `appsettings.json` from release and downloads required models
- **windows-app-deploy.AC2.4 Success:** Deploy verifies SHA256 checksum before extracting
- **windows-app-deploy.AC2.5 Failure:** Deploy rejects artifact with mismatched checksum (tampered zip)
- **windows-app-deploy.AC2.6 Failure:** Deploy refuses to write outside the app's install directory
- **windows-app-deploy.AC2.7 Edge:** Deploy with no previous install (fresh machine) completes successfully including model download

### windows-app-deploy.AC3: Rollback and error recovery
- **windows-app-deploy.AC3.1 Success:** Failed deploy at any step restores backup and restarts previous version
- **windows-app-deploy.AC3.2 Success:** Model download failure (network error) retries 3x with backoff, reports clear error
- **windows-app-deploy.AC3.3 Success:** All deploy actions logged to timestamped audit file
- **windows-app-deploy.AC3.4 Edge:** Deploy when app process is not running (first install or crashed) skips stop step gracefully

### windows-app-deploy.AC4: Desktop integration
- **windows-app-deploy.AC4.1 Success:** Double-clicking `.bat` file on desktop runs full deploy cycle with visible output
- **windows-app-deploy.AC4.2 Success:** `bootstrap-deploy.ps1` copies tooling to `%USERPROFILE%\tools\` and `.bat` to Desktop
- **windows-app-deploy.AC4.3 Success:** Bootstrap is idempotent — safe to re-run without duplicating files or breaking existing installs

### windows-app-deploy.AC5: General-purpose (multi-app)
- **windows-app-deploy.AC5.1 Success:** Adding a new app requires only a registry entry, CI workflow from template, and `.bat` file
- **windows-app-deploy.AC5.2 Success:** SysTTS deploys via the same pipeline as whisper-service with no script modifications
- **windows-app-deploy.AC5.3 Success:** Each app's config and models are isolated in separate install directories

## Glossary

- **whisper-service**: A locally-run Windows application that performs speech-to-text transcription using the Whisper model. One of the two initial target apps for this pipeline.
- **SysTTS**: A locally-run Windows application for text-to-speech synthesis using the Piper neural TTS engine. The second target app and the validation case that the pipeline is truly general-purpose.
- **WSL2 (Windows Subsystem for Linux 2)**: Microsoft's virtualization layer that runs a full Linux kernel inside Windows. Development work happens in WSL2, but the built apps must run natively on Windows.
- **GitHub Actions**: GitHub's built-in CI/CD system. Workflows defined in `.yml` files run automatically on repository events such as a push to `main`.
- **Windows runner**: A GitHub Actions execution environment running Windows. Required here because `dotnet publish` for a `win-x64` target must run on a Windows machine.
- **self-contained (`win-x64`)**: A .NET publish mode that produces a single directory with all dependencies included, targeting the 64-bit Windows platform. No runtime installation required on the end user's machine.
- **GitHub Release**: A GitHub feature that attaches downloadable file assets (binaries, zips, checksums) to a specific git tag. This pipeline uses releases as the artifact distribution mechanism.
- **SHA256 checksum**: A cryptographic hash of a file's contents. The pipeline generates a checksum at build time and the deploy script verifies it before extracting, ensuring the artifact has not been tampered with or corrupted in transit.
- **`app-registry.json`**: A configuration file introduced by this design. It maps app names to deployment metadata (repo slug, Windows process name, install directory, model download sources) so the deploy script is generic and app-agnostic.
- **`appsettings.json`**: The standard .NET configuration file for an application. In this pipeline, it is treated as user-owned state — never overwritten by deploys, and preserved across updates.
- **NuGet**: The package manager for .NET. The pipeline runs `dotnet list package --vulnerable` to detect packages with known CVEs.
- **Hugging Face**: A public model hosting platform used by both whisper-service and SysTTS to distribute their AI model files. The deploy script downloads missing models from Hugging Face on first install.
- **ONNX (Open Neural Network Exchange)**: An open format for storing trained machine learning models. SysTTS's Piper models are distributed in ONNX format.
- **Piper**: An open-source, locally-run neural text-to-speech engine. SysTTS is built on Piper and uses ONNX model files downloaded from Hugging Face.
- **`IOptions` (.NET)**: A .NET dependency injection pattern for typed configuration. Applications using `IOptions` automatically fall back to code-defined defaults for settings keys not present in `appsettings.json`, eliminating the need for config migration in the deploy script.
- **Action pinning (by commit SHA)**: A GitHub Actions security practice where each `uses:` reference specifies an exact commit hash rather than a mutable tag. Prevents a compromised action from altering build behavior without a code change.
- **Idempotent**: A script or operation that produces the same result regardless of how many times it is run. The bootstrap script is idempotent — re-running it on a machine that already has the tooling is safe and non-destructive.

## Architecture

Two-stage pipeline: CI build (GitHub Actions, Windows runner) produces versioned release artifacts; local deploy script (PowerShell, triggered by desktop `.bat`) pulls the latest release and installs it.

**CI stage:** Each Windows app repo contains a `.github/workflows/build-release.yml`. On push to `main`, a Windows runner runs `dotnet publish` (self-contained, `win-x64`), zips the output excluding user-configurable files (`appsettings.json`, `models/`), generates a SHA256 checksum, runs `dotnet list package --vulnerable`, and creates a GitHub Release with the zip and checksum as assets. A default `appsettings.json` is attached separately for first-time installs.

**Deploy stage:** A general-purpose `deploy-app.ps1` script on Windows accepts an app name, looks it up in `app-registry.json`, and executes: download latest release via `gh release download` → verify SHA256 checksum → stop running process → backup config and models → extract new release → restore config (or install defaults if first run) → download missing models from Hugging Face → start app → confirm process is running. Failures at any step trigger rollback from backup.

**Desktop integration:** Each app gets a `.bat` file on the desktop that calls `deploy-app.ps1` with the app name. Double-click to deploy.

**Configuration separation:** All tunable parameters (model size, prompt vocabulary, hotkeys, recording limits, etc.) live in `appsettings.json` and are never overwritten by deploys. Only application binaries are replaced. Config changes never require rebuilds.

## Existing Patterns

Investigation found mature CI/CD patterns in the workspace:

- **stock-analyzer** has a multi-job GitHub Actions pipeline (`dotnet-ci.yml`) with a `build-windows` job on `windows-latest`, and a production deploy workflow (`azure-deploy.yml`) with preflight checks, confirmation gates, and smoke tests. The CI template for Windows apps follows this structure.
- **stock-analyzer** also has a `security-scan` job that the vulnerability scanning step mirrors.
- **whisper-service** has PowerShell install scripts (`install-startup.ps1`, `install-service.ps1`) that handle process management, model directory creation, and startup shortcut creation. The deploy script builds on these patterns for stop/start/model-check logic.
- **SysTTS** has a model download script (`scripts/download-models.ps1`) that fetches ONNX models from Hugging Face. The model download step in the deploy script follows this pattern.
- **claude-env** has a `bootstrap.sh` that does idempotent environment setup with state tracking. The first-time install flow (default config, model download) follows this idempotent pattern.

**New pattern introduced:** The `app-registry.json` mapping is new — no existing equivalent. It centralizes per-app deployment metadata (repo, process name, install directory, model sources) so the deploy script is generic. Adding a new app means adding a registry entry, not modifying the script.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: CI Workflow Template
**Goal:** Reusable GitHub Actions workflow that builds any .NET Windows app and publishes a versioned GitHub Release with checksum.

**Components:**
- CI workflow template in `infrastructure/windows-deploy/build-release.yml` — parameterized for app name, project path, target framework
- Workflow installed into `whisper-service/.github/workflows/build-release.yml` as first consumer
- NuGet vulnerability scanning step (`dotnet list package --vulnerable`)
- SHA256 checksum generation and upload as release asset
- Action versions pinned by SHA, not tag

**Dependencies:** None (first phase)

**Done when:** Push to whisper-service `main` triggers CI, produces a GitHub Release with zip artifact and checksum file. Vulnerability scan runs and would fail the build on known-vulnerable packages.
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Deploy Script and App Registry
**Goal:** General-purpose PowerShell deploy script that can install/update any registered Windows app from GitHub Releases.

**Components:**
- `deploy-app.ps1` in `infrastructure/windows-deploy/` — accepts `-App` parameter, reads registry, executes full deploy lifecycle
- `app-registry.json` in `infrastructure/windows-deploy/` — maps app names to repo, process name, install dir, model config
- Whisper-service entry as first registry entry

**Deploy lifecycle in script:**
1. Download latest release via `gh release download`
2. Verify SHA256 checksum against published checksum file
3. Stop running process by name
4. Backup `appsettings*.json` and `models/` to temp location
5. Extract zip to install directory (`$env:USERPROFILE\Apps\<app>\`)
6. Restore config from backup (or download default `appsettings.json` from release if first install)
7. Check for required model files, download from Hugging Face if missing
8. Start application, confirm process is running
9. On any failure: restore backup, restart old version, report error

**Dependencies:** Phase 1 (needs a release to download)

**Done when:** Running `deploy-app.ps1 -App whisper-service` on Windows downloads the latest release, installs it, preserves config, handles models, and starts the app. Rollback works on simulated failure.
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Desktop Integration and First-Time Bootstrap
**Goal:** One-click `.bat` files and first-time setup that copies deploy tooling to Windows.

**Components:**
- `.bat` template in `infrastructure/windows-deploy/` — parameterized wrapper that calls `deploy-app.ps1`
- Bootstrap script in `infrastructure/windows-deploy/bootstrap-deploy.ps1` — copies deploy script, registry, and `.bat` files to `$env:USERPROFILE\tools\` and Desktop
- First-run detection in `deploy-app.ps1` — installs default config and downloads models on initial deploy

**Dependencies:** Phase 2 (deploy script must exist)

**Done when:** Running `bootstrap-deploy.ps1` on a fresh Windows machine creates the tools directory, copies scripts, places `.bat` on desktop. Double-clicking the `.bat` successfully deploys whisper-service from scratch (first-time install with model download).
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Security Hardening and Audit Logging
**Goal:** Defense-in-depth verification and deploy audit trail.

**Components:**
- Checksum verification logic in `deploy-app.ps1` — rejects artifacts with mismatched SHA256
- Release provenance check — verifies release was created by GitHub Actions (not manual upload)
- Path validation — refuses to write outside install directory
- Audit log in `$env:USERPROFILE\Apps\deploy-log.txt` — timestamped entries for every deploy action
- Rollback verification — test that failed deploys restore previous working state

**Dependencies:** Phase 2 (deploy script to harden)

**Done when:** Deploy rejects a tampered artifact (modified zip with wrong checksum). Deploy refuses to write to paths outside install directory. Failed deploy restores backup and restarts old version. All actions logged with timestamps.
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: SysTTS Onboarding
**Goal:** Validate the pipeline is truly general-purpose by onboarding a second app.

**Components:**
- SysTTS entry in `app-registry.json` with Piper model download config
- CI workflow in `SysTTS/.github/workflows/build-release.yml` (from template)
- Desktop `.bat` for SysTTS

**Dependencies:** Phases 1-4 (full pipeline operational)

**Done when:** SysTTS deploys via double-click `.bat` with the same pipeline as whisper-service. Models download automatically. Config preserved across deploys.
<!-- END_PHASE_5 -->

## Additional Considerations

**Model download reliability:** Hugging Face occasionally rate-limits downloads. Deploy script should retry with backoff (3 attempts, exponential) and report clear error if model download fails rather than leaving a partial file.

**Startup shortcut management:** The deploy script replaces binaries but must also update the Windows Startup shortcut (if installed via `install-startup.ps1`) to point to the new install directory. Otherwise the app won't auto-start after reboot.

**Config migration:** If a new app version adds config keys that don't exist in the user's `appsettings.json`, the app should use code defaults (as .NET `IOptions` already does). No config migration logic needed in the deploy script — this is handled by the application's default values in the settings classes.
