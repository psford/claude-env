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

**Last session:** 2026-06-12 (evening)

**Theme:** Hook test coverage closed — `run-hook-tests.sh` gained `_invoke.sh` driver protocol; 22 fixtures across 3 hooks (agent_worktree_default_guard, agent_working_tree_guard + snapshot pair, regression_test_red_verify); full suite at 26/26 green; mutation tests confirmed fixtures catch the regression classes they claim to. Two commits on `docs/session-state-2026-06-09` (`6af923d`, `bf95c0d`), branch 8 commits ahead of origin, not pushed.

**Next planned task:** Infra cruft audit (see `project_infra_cruft_audit` memory). Patrick switching models for that work. Surfaces: auto-memories (~60 files, highest decay; start here), project-specific CLAUDE.mds across companion repos, accumulated tooling in claude-env (~50+ hooks, manifest entries).

**Pending from this session:** absolute-path enforcement hook (`feedback_absolute_paths_in_handoff`) — originally slated alongside hook tests, deferred. Trigger: "absolute path hook" / "handoff path guard."

---

## Previous: 2026-06-08 → 2026-06-09 (overnight)

**Themes:** photo-portfolio Phase 2 (Slug Schema) execution → SDLC retrospective → claude-env restructured into shared-tooling source-of-truth → Bicep module registry stood up end-to-end.

**Major work completed:**

1. **photo-portfolio Phase 2 — Slug Schema** (PR #11 merged)
   - Pure slugify + collision-suffix helpers in `api/lib/slug.ts`
   - `Post.slug` + `Post.feedDisplay` across all three triplicated Post type mirrors with compile-time drift guard
   - `validatePost` slug rule for published posts; `applyMutation` derives + freezes slug
   - `backfillSlugs` wired into the publish ETag retry loop
   - Manifest schema bumped 1 → 2

2. **SDLC retrospective mitigations** (photo-portfolio PR #12 merged)
   - `npm run check` now chains `tsc --project api/tsconfig.json` so api/'s nodenext moduleResolution is validated by default
   - `playwright.config.ts` and `playwright.smoke.config.ts` → `reuseExistingServer: false`
   - Project hook `.claude/hooks/manifest_mirror_sync_guard.py` (blocks staging 1 or 2 of 3 Post mirror files)
   - New vitest files: `publish.stale.test.ts`, `manifest.v1-backfill.test.ts`, `manifest-type-comments.test.ts`, `validate-error-style.test.ts`
   - Scaffolded `e2e/slug-roundtrip.spec.ts` with `describe.skip` for Phase 6 to activate
   - Vitest 367 → 391 passing; full e2e matrix (chromium + Firefox + Webkit + Mobile Chrome + 4K) green at 91 passed / 39 skipped / 0 failed

3. **claude-env restructure into shared-tooling source-of-truth** (PRs #14–#20, #21, #22, #23, #24 merged)
   - Playwright WSL cage installer + helper (Firefox + Webkit now installable via `wsl.exe --user root` carve-out)
   - Plan-quality hooks: `plan_branch_guard.py`, `defer_forever_guard.py`, `engines_node_guard.py`, `manifest_completeness_guard.py`
   - Plan-quality helpers: `phase_preflight.py`, `phase_pr_check.py`, `validate_ac_coverage.py`
   - Phase plan template at `infrastructure/plan-templates/phase.md.template`
   - Shared helpers: `cf-deploy-preflight.sh` (generic CF preflight), `endpoints.schema.json`, `nvmrc.template`
   - Reusable GH Actions workflows: `windows-service-build-release.yml` (consumed by whisper-service + SysTTS), `azure-deploy-preflight.yml` (consumed by stock-analyzer + road-trip)
   - Bicep modules library at `infrastructure/bicep/modules/`: `key-vault.bicep` + `key-vault-role-assignment.bicep`
   - Bicep publish pipeline live: OIDC federated credential, environment-gated approval, tag-triggered (`bicep/v*`)
   - **`bicep/v1.0.0` published** to `acrstockanalyzerer34ug.azurecr.io/bicep/modules/{key-vault,key-vault-role-assignment}:1.0.0`
   - Tooling manifest 27 → 45 tools, all declared, completeness invariant enforced by hook
   - Root CLAUDE.md gained `Shared Tooling Index` section pointing companion projects at canonical entry points

4. **Companion-repo migrations**
   - whisper-service + SysTTS: `build-release.yml` → 26-line wrapper around claude-env reusable workflow
   - stock-analyzer + road-trip: Azure deploy preflight → `uses:` claude-env reusable + project-preflight job
   - stock-analyzer + road-trip: `BLOCKING` TODO at top of CLAUDE.md flagging the Bicep KV module migration as the next-time-you-touch-this-repo work

**Open PRs anywhere:** zero. PR #10 (photo-portfolio backlog doc) was closed by Patrick at session end.

**Where to start next:**

photo-portfolio Phase 3 — `Token System + Font Prototype Harness`. Plan file:
`/home/patrick/projects/photo-portfolio/docs/implementation-plans/2026-06-07-visual-design/phase_03.md`

Phase 1 + Phase 2 are DONE. Phase 3 is the first visual phase: dark-surround design tokens, Major Third type scale, 2× spacing scale, four font candidates (Fraunces, Newsreader, Recursive, Bagnard) gated behind a localhost `?font=` switcher for prototype, Production picks one winner. **This is the first phase where Firefox e2e visibility actually matters in earnest** — Firefox binaries are now installed and verified, so don't fall back to "chromium-only."

**BLOCKING work in other repos** (not active this session, deferred per Patrick's directive — see top of each repo's CLAUDE.md):
- stock-analyzer: replace inline KV Bicep with `br:acrstockanalyzerer34ug.azurecr.io/bicep/modules/key-vault:1.0.0` reference. Blocking for ALL updates to that repo.
- road-trip: same migration. Blocking for ALL updates to that repo.

**Say "night!"** at end of session to save state.
