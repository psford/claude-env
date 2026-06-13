# Dev-Workspace Infrastructure Audit — 2026-06-12

**Scope:** 9 project repos + the 65-file auto-memory corpus + claude-env's shared-tooling scaffolding.
**Method:** 11 parallel worker agents (one per project / memory-half) produced structured instruction inventories; cross-cutting synthesis done in-session (Opus). Six load-bearing claims independently re-verified by the orchestrator (see Provenance).
**Goal:** find where instructions overlap across projects and design a shared body of knowledge to replace the copy-paste sprawl.

---

## Executive Summary

The duplication you suspected is real and has a single root cause: **claude-env distributes shared *tooling* (hooks, helpers, templates) but has no mechanism to distribute shared *behavioral rules* (Principles, Git Flow, commit protocol, verification discipline, coding standards).** So every repo's CLAUDE.md re-states those rules by hand. stock-analyzer's CLAUDE.md is ~55% near-verbatim copy of claude-env's; the same blocks recur in road-trip, photo-portfolio, SysTTS, and T-Tracker with small per-repo drift.

Three consequences:
1. **Drift & contradiction** — the same rule exists in 6 places and they've fallen out of sync (e.g., "Between tasks" says "check Slack" in one repo and "check WYA/ROADMAP" in another; PR-merge policy is stricter in some repos than others).
2. **Trust erosion** — at least one rule is marked `**BLOCKED**` but its hook is advisory-only (stock-analyzer SPECS). A rule that claims enforcement it doesn't have is worse than no rule.
3. **Memory bloat** — 65 memory files, of which ~22 collapse into 8 overlap clusters, ~5 are stale/done and should be deleted, and ~8 are really CLAUDE.md rules hiding in personal memory.

The fix is a **tiered shared-knowledge layer in claude-env** (universal → stack-tier → project-specific) plus a **sync mechanism** so each repo's CLAUDE.md shrinks to project-specific contracts + a pointer to the shared layer. This is the "Phase 6 bootstrap" that was described in claude-env's CLAUDE.md but never built.

**Recommended first move:** the memory cleanup + the universal-fragment extraction are independent and low-risk — do those first for an immediate win, then tackle the stack tiers and the sync mechanism.

---

## Part 1 — Per-Project Documentation

| Project | What it is | Stack / hosting | CLAUDE.md | Shareable % | Hooks wired |
|---|---|---|---|---|---|
| **stock-analyzer** | Stock analysis web app + WPF data loader | ASP.NET Core, Azure SQL, Docker→Azure App Service (`psfordtaurus.com`) | 389L root + 54L eodhd | ~55% | 2 local (project-specific) |
| **road-trip** | Privacy-first geotagged photo map | ASP.NET Core 8, EF Core, Azure SQL+Blob, MapLibre, Capacitor iOS | 365L (densest, mostly specific) | low (~20%) | 0 (settings.json injects 1 env var) |
| **photo-portfolio** | Photo portfolio + owner admin | TS/Astro, Cloudflare Workers, Azure Functions, Blob+MI | 260L root + 124L api | ~20% | 3 local |
| **T-Tracker** | Real-time MBTA tracker PWA | Vanilla JS, Leaflet, MBTA SSE, Cloudflare Pages (`supertra.in`) | 178L root + 280L src | mostly specific | 2 present, **no settings.json (may be unwired)** |
| **SysTTS** | System TTS Windows service | C#/.NET 8, WinForms, Piper/Sherpa-ONNX, Stream Deck plugin | 394L | mixed; many [WINDOWS-SERVICE] | 0 (**no hooks wired**) |
| **whisper-service** | Speech-to-text Windows service | C#/.NET 8, whisper.cpp | **none** | n/a | 0 |
| **gpu-crash-analyzer** | GPU crash diagnostics | PowerShell 5.1, single-file | 84L | [WINDOWS-UTIL] patterns | 0 |
| **win-audio-analyzer** | Audio-failure diagnostics | PowerShell 5.1, single-file (`/mnt/c`) | 79L | [WINDOWS-UTIL] patterns | 0 |
| **claude-env** | **The hub** — shared tooling source | Python/PS hooks, helpers, Bicep, manifest | 325L + 2 infra | canonical owner | 61 hooks, ~38 helpers |

Full per-project rule inventories: `workers/W01.md`, `W02.md`, `W03.md` on disk; W04–W11 detail folded into Parts 2–4 below.

---

## Part 2 — The Overlap Map (what's shareable, and at what tier)

Three tiers emerged from the `[SHAREABLE]` / `[WINDOWS-SERVICE]` / `[WINDOWS-UTIL]` / `[SPECIFIC]` tagging:

### Tier 0 — Universal (belongs in ALL repos; currently copy-pasted)
These blocks appear near-verbatim in stock-analyzer, road-trip, photo-portfolio, SysTTS (partial), and claude-env:
- **Principles table** (~25 rules: rules-are-hard-blocks, challenge-me, do-it-yourself, diagnose-before-fix, fix-immediately, audit-the-class, preserve-original-media, cite-sources, FOSS-first, no-paid-services, PowerShell-only, etc.)
- **Git Flow** (develop→main, forbidden ops on develop, PR verification protocol, merged-PR-is-dead, pre-commit protocol)
- **Verification discipline** (test-before-suggesting, verify-before-claiming-done)
- **Coding Standards** (naming conventions, testing-not-just-compiling, model-delegation table)
- **Communication / Session Protocol / File Management / Security** sections

**This is the bulk of the duplication.** One canonical copy in claude-env, distributed to all.

### Tier 1 — Stack clusters (shared by a subset)
- **`[WINDOWS-SERVICE]`** → SysTTS + whisper-service: xUnit/Moq/FluentAssertions test stack, `dotnet build/test/run` pre-commit sequence, ILogger-from-DI, async/Task.Run conventions, WinForms+Kestrel threading pattern, config-requires-restart. **whisper-service has NO CLAUDE.md at all** — it could adopt ~80% of SysTTS's instantly from this tier.
- **`[WINDOWS-UTIL]`** → gpu-crash-analyzer + win-audio-analyzer: PS5.1-only, zero-dependency single-file distribution, dot-source test guard (`$MyInvocation.InvocationName -ne '.'`), Event-Viewer provider enumeration pattern, read-only-no-system-modification principle, markdown report output, flush-on-write for crash survival.
- **`[WEB-AZURE]`** → stock-analyzer + road-trip (+ photo-portfolio partial): endpoint-registry pattern, Azure deploy gates, Bicep-module migration, Key Vault secret resolution, `endpoints.json` schema. *(Much of this is already in claude-env hooks — the CLAUDE.md prose around it is what's duplicated.)*

### Tier 2 — Project-specific (stays in each repo)
Domain contracts: stock-analyzer's DTU/coverage-table rules, road-trip's photo-tier/upload contracts, photo-portfolio's manifest schema + slug lifecycle, T-Tracker's route-type matrix + module contracts, SysTTS's hotkey/queue architecture. These are correctly local and should remain.

### Per-repo parameter overrides (the reason a naive copy-paste fails)
A shared layer must support overrides, because repos legitimately diverge:
- **T-Tracker uses `master`**, not `develop`→`main` (verified). Shared Git Flow must be parameterized on branch names.
- **road-trip relaxed the PR-merge policy** (Claude may merge feature→develop without asking) — stricter elsewhere.
- **photo-portfolio & T-Tracker have no GitHub Actions deploy** (manual `wrangler`/Pages) — deploy-gate rules differ.

---

## Part 3 — Memory Corpus Consolidation (65 → ~35 files)

### Overlap clusters to merge (from W10/W11)
| Cluster | Files | Action |
|---|---|---|
| **Verification contract** (largest) | `verify_before_claiming_done`, `trust_contract_for_verification` (master), `dont_let_subagents_skip_verification`, `silent_skip_is_failure`, `curl_doesnt_catch_cors`, `bundle_grep_isnt_verification` | Merge 6 → 1 master file with sub-cases (subagent skips, silent-skip, tool-specific pitfalls as bullets) |
| **PR/branch state** | `always_check_pr_state`, `deploy_implies_pr_merged`, `never_use_current_branch_blindly`, `branch_divergence` | Merge 4 → 1 "never assume git/PR state; verify first" |
| **Accountability** | `any_claude_is_me_no_deflection`, `not_my_fault_is_still_my_problem` | Merge 2 → 1 "I own it all" |
| **Orphan processes** | `verify_subprocess_actually_killed`, `check_orphans_on_resume` | Merge 2 → 1 |
| **Handoff paths** | `absolute_paths_in_handoff`, `implementation_plan_handoff` | Merge 2 → 1 |
| **Credentials** | `check_secure_stores_before_asking_secrets`, `use_env_for_local_deploy` | Merge 2 → 1 |
| **Right-sizing** | `stop_overdesigning`, `right_size_to_scale` | Absorb former into latter |
| **Road-trip prod** | `reference_roadtrip_prod_infra`, `reference_roadtrip_prod_db_access` | Merge 2 → 1 |

### Delete (stale / completed — verified)
- `project_node20_deprecation.md` — ✅ road-trip already on `azure/login@v3`, deadline passed.
- `project_maplibre_migration.md` — ✅ migration shipped (post.html/trips.html on MapLibre, no Leaflet).
- `project_infra_cruft_audit.md` — this audit; delete on completion.
- `project_hook_test_coverage.md` — closed 2026-06-12; trim to a 2-line pointer for the one remaining item (absolute-path hook) or fold into the handoff memory.

### Promote to CLAUDE.md (rules hiding in personal memory)
- `feedback_hook_changes_in_claude_env` → belongs in claude-env Principles ("a fix in a companion repo's shared tooling must also land in claude-env source").
- `feedback_always_give_links`, `feedback_stop_overdesigning` (→ right-size), parts of `user_language_preferences` → universal tier.
- **`project_photo_portfolio_drafts_visibility`** → this is a load-bearing "do NOT 'fix' this" constraint that currently lives ONLY in memory; it must be in photo-portfolio's CLAUDE.md or a new session without memory will "fix" the intended behavior.

Net: 65 → ~35 files, and the index (`MEMORY.md`) is currently accurate (65/65), so it just needs updating alongside.

---

## Part 4 — Defects & Staleness Found Along the Way

**Verified by orchestrator (act with confidence):**
1. **stock-analyzer SPECS enforcement is a lie** — CLAUDE.md marks SPECS `**BLOCKED**` "Enforced by hook," but `spec_staleness_guard.py` only ever `return 0` (advisory). Either make it block or stop claiming it does. *(Directly relevant to last session's trust theme.)*
2. **photo-portfolio env-var doc is wrong** — root CLAUDE.md says `RUN_GATED_TESTS=1`; the actual test reads `RUN_AZURITE_TESTS`. Following the root doc leaves the concurrency test silently skipped. Fix root CLAUDE.md.
3. **claude-env wsl/CLAUDE.md has two `Last verified` headers** (lines 3 & 5) — leftover from an incomplete edit.
4. **non-ascii pre-commit hook** (`project_non_ascii_hook`) genuinely never built — 11 weeks parked.

**Trusted from workers (high confidence, not independently re-verified):**
5. **road-trip stale worktree CLAUDE.md** — `.worktrees/maplibre-migration/CLAUDE.md` is ~2.5 months stale, wrong env-var name (`SA_` vs `RT_`), predates the iOS shell. Delete.
6. **claude-env CLAUDE.md staleness** — lists road-trip as "(future)" though it's live; references `.claude/config/` for companion hooks (actual dir is `.claude/hooks/`); the "Next Steps / Phase 6" section describes a bootstrap that was never built and hooks that now already exist.
7. **Bootstrap gap** — SysTTS, whisper-service, gpu-crash-analyzer, win-audio-analyzer have **zero claude-env hooks wired**; T-Tracker has hook files but no `settings.json` to wire them (possibly dead). The hooks exist in claude-env but nothing installs them into companion repos.
8. **SysTTS settings.local.json** carries stale Windows paths (`C:/Users/.../claudeProjects/SysTTS/`) and a redundant `Bash(*)` wildcard.
9. Stale `Last verified` dates across most repos (stock-analyzer 2026-04-10 + eodhd 2026-02-26; T-Tracker 2026-03-13; SysTTS 2026-02-16; gpu 2026-04-02).

---

## Part 5 — Recommended Solution: Tiered Shared Knowledge + Sync

### Structure (new `shared/claude-md/` in claude-env)
```
claude-env/shared/claude-md/
  00-universal.md            # Tier 0 — Principles, Git Flow, verification, coding std, session, security
  stack-windows-service.md   # Tier 1 — SysTTS, whisper-service
  stack-windows-util.md      # Tier 1 — gpu-crash-analyzer, win-audio-analyzer
  stack-web-azure.md         # Tier 1 — stock-analyzer, road-trip, (photo partial)
```
Each companion CLAUDE.md becomes: **generated shared section(s) + a `CLAUDE.local.md` of project-specific contracts + a small overrides block** (branch names, PR policy, deploy style).

### Distribution mechanism — DECIDED 2026-06-12: Option A (sync script)
**SELECTED — Option A — Concatenation/sync script** (`helpers/sync-claude-md.sh`): assembles each repo's `CLAUDE.md` from the chosen shared fragments + local file, stamped "GENERATED — edit CLAUDE.local.md instead." Re-run to pull updates. Fits the existing manifest/bootstrap style; explicit; greppable. **This also settles decision #2: companion CLAUDE.md becomes a generated artifact; project content lives in `CLAUDE.local.md`.**

Rejected alternatives (recorded for context): *Option B — vendored fragments + drift hook* (more moving parts); *Option C — `@import`* (cross-repo path/versioning awkward, least explicit, unverified).

### PR sequencing (the "big ask," staged to de-risk)
1. **PR-A (claude-env, low risk):** memory consolidation — merge the 8 clusters, delete the 4 stale files, update `MEMORY.md`. *No code impact; immediate context savings.*
2. **PR-B (claude-env, low risk):** fix the verified defects in claude-env's own docs (duplicate header, "(future)" road-trip, `.claude/config/` error, dead Phase-6 section).
3. **PR-C (claude-env):** extract `shared/claude-md/00-universal.md` from the current canonical copy; write `sync-claude-md.sh` (or chosen mechanism). Validate by regenerating claude-env's own CLAUDE.md.
4. **PR-D…(per repo):** migrate each companion CLAUDE.md to `generated universal + CLAUDE.local.md`. Start with **stock-analyzer** (highest duplication, clearest win), then road-trip, photo-portfolio.
5. **PR-E:** stack tiers — author `stack-windows-service.md`, give **whisper-service its first CLAUDE.md** from it; apply windows-util tier to the two PS utilities.
6. **PR-F:** wire the hooks/bootstrap into the unwired repos (SysTTS, whisper-service, the PS utils) — finally building the long-described Phase 6.
7. **Fix-alongside:** the SPECS-enforcement lie and the photo-portfolio env-var doc bug get fixed in their repos' migration PRs.

### Decisions
1. **Distribution mechanism** — ✅ DECIDED: Option A, sync script.
2. **Generated-vs-handwritten** — ✅ DECIDED (implied by #1): generated artifact + `CLAUDE.local.md`.
3. **Sequencing appetite** — OPEN: do PR-A + PR-B now (quick wins), or design the whole shared layer first then execute end-to-end?

---

## Provenance
- **Verified-by-orchestrator:** the 6 claims in the Part-4 "verified" list (commands run this session: grep of azure/login, maplibre/leaflet, spec_staleness_guard returns, photo env-var across docs+test, wsl header lines, hook/branch existence).
- **Trusted-from-workers:** per-project rule inventories and the remaining staleness items — high confidence, structured, but not each independently re-run.
- **Not verified:** exact line counts as they drift; Azure live-state for road-trip Bicep reconciliation (needs `az`, out of scope).

## Methodology
11 worker agents (Sonnet for dense/analytical, Haiku for small projects), one per project + two for the memory corpus halves. Worker file-writes were redirected into per-agent git worktrees by the `agent_worktree_default_guard` hook — surfaced correctly by the `agent_working_tree_guard` hook on every dispatch (the structural safety built last session, working as designed). Adapted mid-run: later workers returned reports as text; synthesis done in-session rather than via 6 critic subagents, since the full corpus (~25k tokens of reports) fit in orchestrator context.
