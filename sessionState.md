# Session State

Say **"hello!"** to restore context from CLAUDE.md and this file.

---

## Environment

| Component | Status | Notes |
|-----------|--------|-------|
| Git | OK | SSH auth configured |
| GitHub | OK | Branch protection, CI/CD via Actions |
| Python | OK | 3.10+ |
| .NET | OK | .NET 8 (if building .NET apps) |
| WSL2 | OK | Linux sandbox available for development |

---

## Quick Start

```bash
# Install git hooks (after clone)
./scripts/install-hooks.sh

# Use in conjunction with app repos (stock-analyzer, road-trip, etc.)
# This is the development environment repo - it contains helpers, hooks, and setup scripts
```

---

## Where We Left Off

**Last session:** 2026-03-28

**Completed this session:**
- Windows App Deployment Pipeline — implemented across 5 phases, 14 tasks, 12 review cycles, 23 issues found and fixed
  - Phase 1: CI workflow template (build-release.yml) — vulnerability scan + build + GitHub Release
  - Phase 2: deploy-app.ps1 — full lifecycle with rollback, checksum verification, provenance check
  - Phase 3: bootstrap-deploy.ps1 + .bat template — one-click desktop deploy
  - Phase 4: Security hardening — path validation, audit logging, shared deploy-functions.ps1
  - Phase 5: SysTTS onboarded as second app (array-format models)
- CI workflows installed and tested in whisper-service and SysTTS repos
- SysTTS default branch renamed from master → main for consistency
- Human testing passed all 8 required tests on Windows
- Bugs found during testing and fixed:
  - Non-ASCII characters (em dash) broke Windows PowerShell 5.1 parser
  - Invalid GitHub Actions SHAs (actions/checkout, actions/setup-dotnet)
  - Path validation rejected install dir itself when targetDir is "."

**PRs:**
- claude-env PR #2: merged (Windows app deployment pipeline)
- whisper-service PR #2: merged (CI workflow with fixed SHAs)
- SysTTS PR #1: merged (CI workflow)

**Repos:**
- claude-env: develop, ahead of main with bug fixes found during testing
- whisper-service: develop, CI workflow active, releases working
- SysTTS: develop, CI workflow active, releases working

**TODO (future session):**
- Create pre-commit hook to block non-ASCII characters in source files (see memory: project_non_ascii_hook.md)
- Merge latest claude-env develop → main (includes post-testing fixes)

**Say "night!"** at end of session to save state.
