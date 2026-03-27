# Windows App Deployment Pipeline Tests

This directory contains automated test scripts for the windows-app-deploy acceptance criteria.

## Automatable Tests (No External Dependencies)

These tests can be run in CI or locally without requiring external infrastructure.

### AC1.5 - Vulnerability Scan Job Exists
**File**: `test_workflow_actions.py::test_ac1_5_vulnerability_scan_job_exists`

Tests that the `build-release.yml` workflow contains:
- A `vulnerability-scan` job that runs `dotnet list package --vulnerable`
- The `build-and-release` job depends on `vulnerability-scan` as a prerequisite

**Run**: `python3 test_workflow_actions.py`

### AC1.6 - GitHub Actions Pinned by SHA
**File**: `test_workflow_actions.py::test_ac1_6_actions_pinned_by_sha`

Tests that all GitHub Actions in `build-release.yml` are pinned to a specific commit SHA.

Verification:
- Parses the workflow YAML
- Extracts all `uses:` statements
- Asserts each matches `owner/action@<40-char-hex-sha>` pattern
- Rejects tags (e.g., `@v1.0`), branches, or unpinned references

**Run**: `python3 test_workflow_actions.py`

### AC4.3 - Bootstrap is Idempotent
**File**: `../test-bootstrap-idempotency.ps1`

Tests that `bootstrap-deploy.ps1` can be run multiple times without errors or side effects.

Verification (in a mock directory):
- Run bootstrap twice in sequence
- Assert both runs exit successfully (code 0)
- Assert no duplicate `.bat` files are created
- Assert tools directory contents are identical after run 1 and run 2
- Assert all required files exist: `deploy-app.ps1`, `app-registry.json`, `deploy-functions.ps1`

**Requirements**: PowerShell 5.0+ on Windows (can run in WSL2 PowerShell)

**Run**: `powershell -ExecutionPolicy Bypass -File test-bootstrap-idempotency.ps1`

## Non-Automatable Tests (Integration)

These tests require external dependencies or real infrastructure and are verified manually:

| AC ID | Description | Why Not Automated | Verification |
|-------|-------------|-------------------|--------------|
| AC1.2 | Release includes SHA256 checksum file | Requires a real GitHub release | See test-requirements.md |
| AC1.3 | Release excludes appsettings.json and models/ | Requires downloading release zip | See test-requirements.md |
| AC1.4 | Default appsettings.json attached as asset | Requires real GitHub release | See test-requirements.md |
| AC1.7 | Build fails with vulnerable package (negative test) | Requires destructive push to trigger CI | See test-requirements.md |
| AC2.1-AC2.7 | Deploy script behavior | Requires real Windows environment, releases, network | See test-requirements.md |
| AC3.1-AC3.4 | Deploy error handling and logging | Requires real deploy environment | See test-requirements.md |
| AC5.2-AC5.3 | Multi-app deployment | Requires real releases for multiple apps | See test-requirements.md |

Full details: See `/docs/implementation-plans/2026-03-26-windows-app-deploy/test-requirements.md`

## Running All Automated Tests

### Linux/WSL2 (Python tests only):
```bash
cd infrastructure/windows-deploy/tests
python3 test_workflow_actions.py
```

### Windows (all tests):
```powershell
cd infrastructure\windows-deploy\tests
python test_workflow_actions.py
powershell -ExecutionPolicy Bypass -File ..\test-bootstrap-idempotency.ps1
```

## Test Output Format

Tests output results in human-readable format with colored status:
- ✓ PASS: Green checkmark
- ✗ FAIL: Red X

Failed tests exit with code 1. Successful tests exit with code 0.

## CI Integration

These Python tests can be integrated into GitHub Actions:

```yaml
- name: Run workflow validation tests
  run: |
    python3 infrastructure/windows-deploy/tests/test_workflow_actions.py
```

The PowerShell idempotency test requires Windows PowerShell and can be added to Windows runner jobs.
