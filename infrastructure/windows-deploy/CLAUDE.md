# Windows App Deployment Pipeline

Last verified: 2026-03-27

## Purpose

Automated deployment pipeline for Windows desktop applications. Downloads CI-built releases from GitHub, verifies integrity, installs to `%USERPROFILE%\Apps\<AppName>`, and manages process lifecycle with rollback on failure.

## Contracts

- **Exposes**: `deploy-app.ps1 -App <name>` as the single entry point for deploying any registered app
- **Guarantees**:
  - Only CI-built releases are deployed (provenance check via `Assert-ReleaseProvenance`)
  - SHA256 checksum verification before extraction
  - Path traversal protection (`Assert-PathWithinInstallDir` on every write)
  - Automatic rollback on failure (restores backup config + models, restarts old process)
  - Audit log at `%USERPROFILE%\Apps\deploy-log.txt` for every action
  - Config preservation across upgrades (appsettings*.json, models/)
  - Model downloads with retry + exponential backoff (3 attempts)
- **Expects**: `gh` CLI installed and authenticated, app registered in `app-registry.json`, GitHub releases with `.zip`, `.sha256`, and `appsettings.default.json` artifacts

## Dependencies

- **Uses**: GitHub CLI (`gh`), GitHub Releases (artifact source), Hugging Face (model downloads), GitHub release assets (model downloads)
- **Used by**: `bootstrap-deploy.ps1` (first-time setup), `.bat` desktop shortcuts, CI workflow (`build-release.yml`)
- **Boundary**: These scripts deploy pre-built artifacts only. They do not build, test, or modify application source code.

## Key Files

- `deploy-app.ps1` -- Main deployment script (download, verify, backup, extract, restore config, start)
- `deploy-functions.ps1` -- Shared functions: `Write-AuditLog`, `Assert-ReleaseProvenance`, `Assert-PathWithinInstallDir`
- `bootstrap-deploy.ps1` -- First-time setup: creates `~/tools/`, copies scripts, creates desktop shortcuts
- `app-registry.json` -- App definitions (repo, process name, install dir, model sources)
- `build-release.yml` -- GitHub Actions workflow template for building and publishing releases
- `Deploy-App.bat.template` -- Template for desktop deploy shortcuts
- `test-audit-logging.ps1` -- Tests for audit log functionality
- `test-path-validation.ps1` -- Tests for path traversal protection

## Registered Apps

- `whisper-service` -- Speech-to-text service (psford/whisper-service), models from Hugging Face
- `systts` -- Text-to-speech service (psford/SysTTS), models from Hugging Face + GitHub releases

## Gotchas

- App registry supports two model formats: object format (whisper-service, reads model name from appsettings.json) and array format (systts, explicit file lists)
- `bootstrap-deploy.ps1` must be run from Windows PowerShell (not WSL2) since it creates Windows shortcuts and copies to Windows paths
- The `.gitignore` has a specific exclusion (`!infrastructure/windows-deploy/*.ps1`) to allow these scripts to be committed despite the global `*.ps1` ignore rule
