# SDLC Retrospective Mitigations — WSL2 Claude Code Sandbox

**Date:** 2026-03-22
**Session:** WSL2 sandbox implementation (phases 1-8)

## Status

4 of 13 mitigations implemented:
- [x] #1 ShellCheck pre-commit hook (ff314eb)
- [x] #4 Stderr suppression guard (05d38e2)
- [x] #5 Plan config drift guard (e68ff27)
- [x] #9 PostToolUse hook tests (240e343)

## Remaining 9 — Implement in WSL2 Session

### #7 DI Wiring Integration Tests (M effort)
Create `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Integration/ProgramDiWiringTests.cs` using `WebApplicationFactory` to test both SQL and JSON DI branches in Program.cs. Add `public partial class Program {}` to end of Program.cs. Add `Microsoft.AspNetCore.Mvc.Testing` package to test project.

### #11 Setup Functional Verification (M effort)
Create `infrastructure/wsl/verify-setup.sh` that runs every automatable AC (Bash(*) check, toolchain versions, .env completeness, hook tests, SQL TCP connectivity). Update wsl-setup.sh to call it instead of version-only summary.

### #10 Secrets Round-Trip Test (M effort)
Create `infrastructure/wsl/test-secrets-roundtrip.sh` that validates Key Vault ↔ .env consistency. Checks all expected secrets exist in Key Vault, all expected .env keys are non-empty, WSL SQL passwords are set, GitHub App private key file exists.

### #2 ShellCheck CI Job (S effort)
Add `shell-lint` job to `.github/workflows/dotnet-ci.yml`. Add `infrastructure/wsl/**` to path filters. Runs `shellcheck --severity=warning --shell=bash` on all `.sh` files.

### #12 AC Verification Status Tracker (S effort)
Create `infrastructure/wsl/ac-status.json` (tracks human-verified AC status), `infrastructure/wsl/ac-tracker.py` (CLI: status/verify/stale commands), `.claude/hooks/ac_staleness_guard.py` (advisory warning when verified ACs become stale).

### #6 Markdown Table Total Checker (M effort)
Create `helpers/hooks/check_md_table_totals.py` pre-commit hook. Detects "Total" rows in markdown tables and validates arithmetic. Register in `.pre-commit-config.yaml`.

### #3 Bash Syntax Write Guard (S effort)
Create `.claude/hooks/shellcheck_write_guard.py` PreToolUse hook on Write to `.sh` files. Runs `bash -n` on content before allowing the write. Catches syntax errors at write time.

### #8 CI Env Var Matrix (S effort)
Add matrix strategy to `build-and-test` job in `dotnet-ci.yml`. Run tests with and without `WSL_SQL_CONNECTION` set so both DI branches are exercised in CI.

### #13 JS Display-Cap Guard (S effort)
Extend `.claude/hooks/workaround_guard.py` to detect `Math.min(val, 100)` patterns in JS UI files (wwwroot, components, views). Prevents display-layer symptom masking.

## Known Issue: CI Path Filter Too Broad

**TODO:** The `.github/workflows/dotnet-ci.yml` path filter includes `docs/**` and `CLAUDE.md`, which triggers a full .NET CI run for doc-only changes (like this retro file). Fix the path filter to only trigger on code-relevant docs, not retrospectives or implementation plans.
