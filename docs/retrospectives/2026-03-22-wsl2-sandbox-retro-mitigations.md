# SDLC Retrospective Mitigations — WSL2 Claude Code Sandbox

**Date:** 2026-03-22
**Session:** WSL2 sandbox implementation (phases 1-8)

## Status

13 of 13 mitigations implemented:
- [x] #1 ShellCheck pre-commit hook (ff314eb)
- [x] #4 Stderr suppression guard (05d38e2)
- [x] #5 Plan config drift guard (e68ff27)
- [x] #9 PostToolUse hook tests (240e343)
- [x] #7 DI Wiring Integration Tests — WSL2 session
- [x] #11 Setup Functional Verification — WSL2 session
- [x] #10 Secrets Round-Trip Test — WSL2 session
- [x] #2 ShellCheck CI Job — WSL2 session
- [x] #12 AC Verification Status Tracker — WSL2 session
- [x] #6 Markdown Table Total Checker — WSL2 session
- [x] #3 Bash Syntax Write Guard — WSL2 session
- [x] #8 CI Env Var Matrix — WSL2 session
- [x] #13 JS Display-Cap Guard — WSL2 session

## Implemented in WSL2 Session (2026-03-21)

### #7 DI Wiring Integration Tests (M effort)
Created `projects/stock-analyzer/tests/StockAnalyzer.Core.Tests/Integration/ProgramDiWiringTests.cs` using `WebApplicationFactory` to test both SQL and JSON DI branches in Program.cs. Added `public partial class Program {}` to end of Program.cs. Added `Microsoft.AspNetCore.Mvc.Testing` package to test project. 14 tests (7 per branch), serialized via xUnit collection to prevent env var race conditions.

### #11 Setup Functional Verification (M effort)
Created `infrastructure/wsl/verify-setup.sh` that runs every automatable AC (toolchain versions, .env completeness, hook tests, SQL TCP connectivity). Prints color-coded summary table.

### #10 Secrets Round-Trip Test (M effort)
Created `infrastructure/wsl/test-secrets-roundtrip.sh` that validates Key Vault ↔ .env consistency. Checks all expected secrets exist in Key Vault, all expected .env keys are non-empty, WSL SQL passwords are set, GitHub App private key file exists.

### #2 ShellCheck CI Job (S effort)
Added `shell-lint` job to `.github/workflows/dotnet-ci.yml`. Added `infrastructure/wsl/**` to path filters. Runs `shellcheck --severity=warning --shell=bash` on all `.sh` files. Fixed existing ShellCheck warning in `wsl-setup.sh` (SC2046 unquoted command substitution).

### #12 AC Verification Status Tracker (S effort)
Created `infrastructure/wsl/ac-status.json` (tracks human-verified AC status), `infrastructure/wsl/ac-tracker.py` (CLI: status/verify/stale/reset commands), `.claude/hooks/ac_staleness_guard.py` (advisory warning on push when verified ACs become stale). Registered in settings.local.json as PostToolUse hook.

### #6 Markdown Table Total Checker (M effort)
Created `helpers/hooks/check_md_table_totals.py` pre-commit hook. Detects "Total" rows in markdown tables and validates arithmetic. Registered in `.pre-commit-config.yaml`.

### #3 Bash Syntax Write Guard (S effort)
Created `.claude/hooks/shellcheck_write_guard.py` PreToolUse hook on Write to `.sh` files. Runs `bash -n` on content before allowing the write. Catches syntax errors at write time. Registered in settings.local.json.

### #8 CI Env Var Matrix (S effort)
Added matrix strategy to `build-and-test` job in `dotnet-ci.yml`. Runs tests with and without `WSL_SQL_CONNECTION` set so both DI branches are exercised in CI. Artifact names include matrix variant.

### #13 JS Display-Cap Guard (S effort)
Extended `.claude/hooks/workaround_guard.py` with `JS_CAP_PATTERNS` regex to detect `Math.min(val, 100)`, `Math.max(0, Math.min(...)`, ternary caps, and `.clamp()` patterns in JS UI files (wwwroot, components, views). Prevents display-layer symptom masking.

## Known Issue: CI Path Filter Too Broad

**TODO:** The `.github/workflows/dotnet-ci.yml` path filter includes `docs/**` and `CLAUDE.md`, which triggers a full .NET CI run for doc-only changes (like this retro file). Fix the path filter to only trigger on code-relevant docs, not retrospectives or implementation plans.
