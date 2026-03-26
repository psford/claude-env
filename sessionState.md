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

**Last session:** 2026-03-25

**Completed this session:**
- MapLibre GL JS migration (PR #8, merged) — replaced Leaflet with MapLibre v5.21.0 across all maps
  - 4 phases: CDN swap, markers/popups, route/navigation, cleanup
  - Human testing found and fixed: route layer timing, popup styling/overflow, single-popup enforcement, view page fullscreen
  - MapTiler vector tiles with domain-restricted API key
- Bulk photo upload (PR #9, merged) — multi-select from iOS picker
  - uploadQueue.js: 3-concurrent uploads, retry, floating status bar
  - GPS triage: tagged photos upload immediately, 1-5 untagged get pin-drop, 6+ skipped
  - Rate limit raised 20→200/hour
- EXIF rotation fix (PR #10, merged) — portrait photos stored upright via SKCodec.EncodedOrigin
- GPS extraction fix (PR #11, merged) — NaN validation, diagnostic logging
- exifr full build (PR #12, merged) — lite build crashed on iOS timestamp extraction, couldn't parse DNG
- Photo cache headers (PR #13, merged) — immutable 1-year cache on photo serving endpoint
- SDLC Retrospective — identified 4 themes, implemented 9 mitigations:
  - pre_push_merged_branch_guard.py, cherry_pick_guard.py, plan_commit_guard.py
  - dotnet_process_guard.py, library_intro_guard.py, constant_change_test_guard.py
  - js_module_coverage_guard.py, native git pre-push hook, worktree_setup.sh
- Database fix: manually applied MakeTakenAtNullable migration, granted ALTER on roadtrip schema to wsl_claude

**Repos:**
- claude-env: develop, hooks updated
- road-trip: main, both PRs merged, deployed to prod

**Say "night!"** at end of session to save state.
