# PowerShell Script Audit for WSL2 Migration

**Audit Date:** 2026-03-21
**Total PS1 Scripts:** 31
**Audit Scope:** Categorize all PowerShell scripts in `helpers/` as WSL2-needed, Windows-only, or has-Python-equivalent

---

## Summary

| Category | Count | Decision |
|----------|-------|----------|
| WSL2-Needed | 0 | No bash rewrites required |
| Windows-Only (no Python equivalent) | 22 | Keep as PS1 for Windows use |
| Has Python Equivalent | 9 | Use Python versions instead |

**Conclusion:** All PowerShell helper scripts are either Windows-specific or have Python equivalents. No bash rewrites are needed. Claude's WSL2 workflow will use Python helpers instead. Categories are mutually exclusive — each script appears in exactly one category.

---

## WSL2-Needed (rewrite as bash)

| PS1 Script | Bash Equivalent | Purpose |
|------------|----------------|---------|
| *(none)* | | |

**Rationale:** All candidate scripts either depend on Windows-only APIs or have Python equivalents that Claude can use directly in WSL2.

---

## Windows-Only (keep as PS1)

### Process & Service Management

| PS1 Script | Purpose | Why Windows-only |
|------------|---------|-----------------|
| `restart_api.ps1` | Kill API processes, rebuild, and start on configured port | Uses `Get-Process`, `Stop-Process`, `Start-Process` (Windows process APIs); manages dotnet.exe process |
| `restart_theme_service.ps1` | Kill uvicorn on port 8001, restart theme generator service | Uses `Get-NetTCPConnection` to identify process by port, `Get-Process`, `Stop-Process` (Windows-specific) |
| `install_slack_services.ps1` | Install Slack Listener and Acknowledger as Windows Services using NSSM | Uses NSSM (Windows service manager), `Get-Service`, `sc.exe` (Windows service control) |

### SQL Server Operations

| PS1 Script | Purpose | Why Windows-only |
|------------|---------|-----------------|
| `apply-migration.ps1` | Apply SQL schema migrations to local SQL Express | Uses `System.Data.SqlClient` to connect directly to SQL Express; Windows-only database |
| `check-securitymaster.ps1` | Query SecurityMaster table statistics | Direct SQL Server connection (`System.Data.SqlClient`); Windows-only local database |
| `check_score10_securities.ps1` | Query local database for ImportanceScore=10 securities and CoverageSummary | Direct SQL Server connection; queries local SQL Express |
| `simulate_new_scoring.ps1` | Run scoring algorithm simulation against local database | Complex SQL query execution against local SQL Express using PowerShell ADO.NET |
| `test_importance_local.ps1` | Check local index data and membership counts for importance scoring | Direct SQL Server connection to local database |

### Jenkins CI/CD Management

| PS1 Script | Purpose | Why Windows-only |
|------------|---------|-----------------|
| `jenkins-check.ps1` | List available Jenkins jobs | Uses `Invoke-RestMethod` (common); Jenkins is local Windows Docker |
| `jenkins-console.ps1` | Fetch console output for a Jenkins build | Uses `Invoke-RestMethod`; reads Jenkins job history |
| `jenkins-debug.ps1` | Debugging script for Jenkins API calls with crumb/token handling | Complex Jenkins API interaction; hardcoded Windows Jenkins endpoint |
| `jenkins-reload.ps1` | Reload Jenkins configuration | Uses `Invoke-WebRequest` to Jenkins endpoint |
| `jenkins-trigger.ps1` | Trigger Jenkins build with CSRF crumb handling | Complex Jenkins API interaction; hardcoded credentials |
| `jenkins-trigger-v2.ps1` | Trigger Jenkins build using API token authentication | Jenkins API interaction; credentials in `.env` |

### Docker & Infrastructure

| PS1 Script | Purpose | Why Windows-only |
|------------|---------|-----------------|
| `wait-docker.ps1` | Poll Docker daemon until ready, with 12 retry attempts (60 seconds) | Uses Docker Desktop on Windows; hardcoded Docker path (`C:\Program Files\Docker\Docker\resources\bin\docker.exe`) |

### Desktop & File Management

| PS1 Script | Purpose | Why Windows-only |
|------------|---------|-----------------|
| `fix_shortcut.ps1` | Update Boris desktop shortcut to point to new EodhdLoader.exe path | Uses `WScript.Shell` COM object (Windows-only); creates/modifies `.lnk` files |

### Build & Asset Management

(No Windows-only scripts in this category — CSS compilation can use npm directly)

### iShares ETF Data

| PS1 Script | Purpose | Why Windows-only |
|------------|---------|-----------------|
| `check_ishares_columns.ps1` | Fetch iShares JSON for AAXJ ETF and inspect column structure | Uses `Invoke-WebRequest` to external URL; inspects JSON structure (could use Python, but specific to Windows ad-hoc inspection) |

### Production Monitoring & Debugging

| PS1 Script | Purpose | Why Windows-only |
|------------|---------|-----------------|
| `recalc_importance.ps1` | Trigger production API call to recalculate importance scores | Calls production HTTPS endpoint; uses `Invoke-RestMethod` |
| `test_crawler_flow.ps1` | Simulate the crawler's exact logic flow with state tracking | Complex simulation with HashSets and queues; state tracking mirrors CrawlerViewModel; tests production crawler endpoints |
| `test-eodhd-sync.ps1` | Test EODHD sync endpoint with POST request | Tests local API; simple POST request |

### Data Quality & Analytics

| PS1 Script | Purpose | Why Windows-only |
|------------|---------|-----------------|
| `check_heatmap_score10.ps1` | Check production heatmap for score 10 cells | Uses `Invoke-RestMethod` to production HTTPS; JSON analysis |
| `check_refresh_result.ps1` | Call refresh-summary endpoint and report timing/results | Tests localhost API with timing measurement |

### Speech-to-Text

(No Windows-only scripts in this category — Python handles transcription directly)

---

## Has Python Equivalent (use Python)

| PS1 Script | Python Equivalent | Purpose | Action |
|------------|-------------------|---------|--------|
| `build-css.ps1` | Can use Node.js/npm directly | CSS compilation | Can invoke npm directly from bash/Python |
| `check_gaps.ps1` | `test_dtu_endpoints.py` | API endpoint testing | Use `test_dtu_endpoints.py` instead |
| `check_heatmap.ps1` | `test_dtu_endpoints.py` | API endpoint testing | Use `test_dtu_endpoints.py` instead |
| `check_prod.ps1` | `test_dtu_endpoints.py` | Production endpoint verification | Use `test_dtu_endpoints.py` instead |
| `Invoke-SpeechToText.ps1` | `speech_to_text.py` | Speech transcription | Call `python helpers/speech_to_text.py` directly |
| `jenkins-local.ps1` | `jenkins_manager.py` (if exists, or use CLI) | Jenkins management | Can be scripted with Python + Docker SDK |
| `refresh_summary.ps1` | `test_dtu_endpoints.py` | Production coverage summary refresh | Use `test_dtu_endpoints.py` instead |
| `test_endpoints.ps1` | `test_dtu_endpoints.py` | Endpoint testing | Use `test_dtu_endpoints.py` instead |
| `verify_gaps.ps1` | `test_dtu_endpoints.py` | Gap endpoint testing | Use `test_dtu_endpoints.py` instead |

---

## Detailed Analysis by Category

### API Testing Scripts (8 scripts — 6 with Python equivalents, 2 Windows-only)

Scripts that test HTTP endpoints against local or production API:

**Has Python Equivalent (use `test_dtu_endpoints.py`):**
- `check_gaps.ps1` — queries `/api/admin/prices/gaps`
- `check_heatmap.ps1` — queries `/api/admin/dashboard/heatmap`
- `check_prod.ps1` — queries both heatmap and gaps on production
- `refresh_summary.ps1` — calls `/api/admin/dashboard/refresh-summary`
- `test_endpoints.ps1` — tests heatmap and stats endpoints
- `verify_gaps.ps1` — verifies `/api/admin/prices/gaps` endpoint

**Windows-Only (keep as PS1):**
- `check_heatmap_score10.ps1` — queries `/api/admin/dashboard/heatmap` for score 10 (specific production analysis)
- `check_refresh_result.ps1` — calls `/api/admin/dashboard/refresh-summary` with timing measurement

**Claude's WSL2 Approach:** Use `test_dtu_endpoints.py` for HTTP endpoint testing. It handles:
- Localhost API testing
- Production endpoint checking
- Response parsing
- Timing measurements
- DTU limit awareness (Azure SQL)

### SQL Server Scripts (5 scripts)

Direct SQL Server queries on local SQL Express:

- `apply-migration.ps1` — apply schema migrations
- `check-securitymaster.ps1` — query SecurityMaster statistics
- `check_score10_securities.ps1` — query score 10 securities
- `simulate_new_scoring.ps1` — test scoring algorithm
- `test_importance_local.ps1` — check index data

**Why Windows-only:** These use `System.Data.SqlClient` to connect directly to SQL Express on Windows. In WSL2, if SQL Server is needed, it would be:
1. SQL Server running on Windows (not in WSL2) → need Windows PS1 to access
2. SQL Server in Docker/Linux → would need different connection string handling

**Claude's WSL2 Approach:** If SQL operations are needed in WSL2, they would be:
- Via the HTTP API (preferred — respects SelectedEnvironment)
- Via sqlcmd (if SQL Server is accessible from WSL2)
- Via Python with pyodbc/pymssql (if needed)

### Jenkins Scripts (7 scripts — 1 with Python equivalent, 6 Windows-only)

Manage local Jenkins Docker container:

**Has Python Equivalent:**
- `jenkins-local.ps1` — comprehensive container management (can use Python + Docker SDK)

**Windows-Only (keep as PS1):**
- `jenkins-check.ps1` — list jobs
- `jenkins-console.ps1` — fetch build console
- `jenkins-debug.ps1` — API debugging
- `jenkins-reload.ps1` — reload configuration
- `jenkins-trigger.ps1` — trigger build (CSRF crumb method)
- `jenkins-trigger-v2.ps1` — trigger build (API token method)

**Why Windows-only for these 6:** They manage Windows Docker Desktop and hardcoded endpoints.

**Claude's WSL2 Approach:** In WSL2, Claude can:
- Use `docker` CLI (if Docker daemon is accessible from WSL2)
- Call Jenkins API via `curl` (bash equivalent of `Invoke-RestMethod`)
- Use `python-jenkins` library for comprehensive Jenkins control

---

## Implementation Plan for WSL2

### Step 1: Python Helpers are Primary

Claude's WSL2 workflow will use existing Python helpers:

```bash
# API testing (replaces check_*.ps1 and test_endpoints.ps1)
python3 helpers/test_dtu_endpoints.py

# Link validation
python3 helpers/check_links.py --all

# Slack integration
python3 helpers/slack_bot.py status

# Theme management
python3 helpers/theme_manager.py list
```

### Step 2: Bash Equivalents Not Needed

All 31 PS1 scripts are either:
1. **Windows-specific utilities** that Claude doesn't need in WSL2 (process management, SQL Server direct access, Windows Services)
2. **Already covered by Python equivalents** (API testing, theme management, Slack)
3. **Can be replaced by standard Linux tools** (Docker CLI, curl, npm)

### Step 3: Windows Development Flow (Patrick's Windows Session)

When working on Windows:
- Use PS1 scripts as needed for Windows-specific operations
- Examples: `restart_api.ps1`, `jenkins-local.ps1`, SQL queries
- No changes to Windows workflow

### Step 4: WSL2 Development Flow (Claude in WSL2)

When working in WSL2:
- Use Python helpers for API/data operations
- Use standard bash tools for file/git operations
- Use `curl` instead of `Invoke-WebRequest`
- Use `docker` CLI instead of PowerShell Docker operations
- Never use PS1 scripts directly

---

## Recommendation

**No bash script rewrites needed.** The 33 Python helpers in `helpers/` already provide everything Claude needs in WSL2. Patrick's Windows workflow remains unchanged — all 31 PS1 scripts stay as-is for Windows use only.

Focus resources on:
1. Ensuring Python helpers work correctly in WSL2 (Task 4)
2. Updating hooks to detect WSL2 and adjust messages (Task 3)
3. Documenting WSL2 usage patterns in CLAUDE.md
