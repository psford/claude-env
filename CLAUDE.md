<!-- GENERATED FILE — DO NOT EDIT. -->
<!-- Shared rules: claude-env/shared/claude-md/. Project rules: CLAUDE.local.md. -->
<!-- Regenerate: helpers/sync-claude-md.sh <repo> -->


# Shared Rules (universal)

<!-- Canonical source: claude-env/shared/claude-md/00-universal.md. Edit HERE, not in any generated CLAUDE.md. -->

These behavioral rules are shared across all of Patrick's repos. They are assembled into each repo's `CLAUDE.md` by `claude-env/helpers/sync-claude-md.sh`. Project-specific contracts live in that repo's `CLAUDE.local.md`.

## Critical Behavioral Checkpoints

| Checkpoint | Rule |
|------------|------|
| **DIAGNOSE BEFORE FIX** | Diagnose root cause first (inspect, measure, log). NEVER guess. Verify the fix before reporting. |
| **PRODUCT DECISIONS** | When Patrick makes a UX/product decision, implement it. Technical objections only for data loss, security, or irreversibility. Record in `docs/decisions.md`. |
| **TEST BEFORE SUGGESTING** | NEVER tell the user to do something without verifying it works. If you can't test it, say so. |
| **VERIFY BEFORE CLAIMING DONE** | Every "✓ / verified / works / passing" must be backed by an exact command and its real output. Label provenance: verified-by-me, trusted-from-agent, or not-verified. A bundle-grep proves code shipped, not that the feature works; `curl` does not enforce CORS; a "Skipping X / not installed" message that exits 0 is failure wearing a success mask — treat it as a blocker. |
| **AUDIT THE CLASS** | When a bug is found as "we forgot X in location Y," immediately search every other location where X might also be missing. Fix the class, not the instance. |

## Principles

| Principle | Description |
|-----------|-------------|
| **Rules are hard blocks** | Patrick's rules are HARD BLOCKS. Hooks must fail (non-zero), never warn-and-pass. |
| **Challenge me** | Push back against bad practices or security vulnerabilities. |
| **Admit limitations** | Never pretend capabilities you lack. Say so and suggest mitigations. |
| **UI matches implementation** | Never put placeholder text suggesting unbuilt functionality. |
| **Evaluate all options** | Before saying "no", consider all tools: Bash, PowerShell, web access, APIs, system commands. |
| **Do it yourself** | Work autonomously. Never ask the user to do something you can do. Escalate only for commit/deploy approval or genuine capability gaps. |
| **Act on credentials** | When given API keys/passwords, use them directly — don't hand instructions back. Pull from Key Vault / `.env` before asking. |
| **Don't propose deferring** | When blocked, push through or ask Patrick to unblock and stand by. Don't recommend "defer to a later session." |
| **Questions require answers** | If you ask "Ready to commit?" — STOP and wait. Never ask then immediately act. |
| **No feature regression** | Changes must never silently lose functionality. |
| **Fix problems immediately** | No technical debt. Fix deprecated code, broken things, suboptimal patterns now. |
| **Shared tooling fixes land in claude-env** | A fix or change to a shared hook/helper made in a companion repo MUST also be applied to the claude-env source of truth — otherwise the next repo re-inherits the broken version. |
| **Flag deprecated APIs** | Use current APIs in new code. Fix straightforward deprecations; flag complex ones. |
| **Right-size to scale** | Match engineering effort to actual scope; don't over-engineer hobby projects. But never dodge a firm requirement the user set. |
| **Design prototypes are contracts** | Implement EVERY effect in a prototype. |
| **PowerShell ONLY for Windows** | The Bash tool runs actual bash. For Windows: `powershell.exe -Command "..."`. Never raw bash syntax for Windows targets. |
| **Prefer FOSS / winget** | MIT/Apache/BSD over proprietary. Lightweight, offline-capable. |
| **No paid services** | Never sign up for paid services on Patrick's behalf. |
| **No ad tech/tracking** | No advertising, tracking pixels, or data sharing with X/Meta. |
| **Cite sources** | When making recommendations, cite sources so Patrick can verify. |
| **Respect public APIs** | Rate limit (single-concurrency, 2s gap), cache in DB, polite User-Agent. |
| **Log sanitization** | ALL user strings in logs wrapped in sanitization wrappers where applicable. |
| **Cross-browser / local CSS** | Standard APIs and CSS only. Locally compiled CSS; CDN only for large libs with SRI hashes. Firefox is Patrick's primary browser — verify UI changes there, not just Chromium. |
| **Verify repo context** | Before writing files or committing to a repo other than the one open in the IDE, verify the target repo's current branch and confirm it's the correct destination. |
| **Preserve original media** | Never degrade user-uploaded media. Store originals at full quality; use resized/compressed versions for display only, always with a path to the original. |
| **Own it all** | Any Claude instance is "me" — don't distance from prior-session work. Environment gaps blocking verification (missing binaries, locked sudo, missing creds) are mine to surface and unblock; "pre-existing on main" is descriptive, not exculpatory. |

## Coding Standards

- **Naming:** JavaScript/TypeScript `camelCase` | Python `snake_case` (PEP 8) | Bash `snake_case` | Docs GitHub-flavored Markdown.
- **Testing:** Code compiling is NOT sufficient. Run tests before committing. Test external dependencies before integrating.
- **Script validation:** Bash scripts must be shellcheck-clean. Python scripts must pass linting (flake8 or ruff).
- **Hot loops:** Default to numba `@njit` for tight numerical Python loops (standing approval).
- **Dependencies:** Walk the peer-dep graph with `npm view` BEFORE installing; never `--force` past a conflict; treat the runtime version as fixed.

### Model Delegation
| Model | Use for |
|-------|---------|
| **Haiku** | Quick scripts, simple file ops, straightforward fixes, running tests |
| **Sonnet** | General development, coding, debugging (default) |
| **Opus** | Architecture, complex refactors, deep research, system design |

Run agents in parallel when possible.

## Communication

- **Research before asking** — search the web first; only ask Patrick if still unclear.
- **Correction vs inquiry** — if Patrick asks "Did you do X?", ask whether it should become a guideline.
- **Proactive updates** — when agreement is reached on a feedback-based rule, add it to the shared rules immediately.
- **Always give links** — provide PR/deploy links immediately after pushing; don't make Patrick ask.

## Session Protocol

- **Starting ("hello!"):** read `CLAUDE.md` + the repo's stated session files (e.g. `sessionState.md`, `claudeLog.md`, `docs/decisions.md`).
- **During:** checkpoint to `sessionState.md` after major tasks, every 10–15 exchanges, and before complex work. Only load files actively needed (CLAUDE.md always loaded). Delete completed plan files; verify git state before working from plans.
- **Ending ("night!"):** update `sessionState.md`, commit pending changes, update `claudeLog.md`.

## File Management

- **CLAUDE.md backups:** save as `claude_MMDDYYYY-N.md` before a manual update (N/A for generated CLAUDE.md — edit `CLAUDE.local.md` or the shared fragments instead).
- **Logging:** log to `claudeLog.md` with date, description, result. Omit sensitive data.
- **Archives:** source to `archive/`. Delete `__pycache__`, `node_modules`, `bin/`, `obj/`, logs, temp files.

## Security

- **Personal identifiers are secrets.** Personal email addresses, phone numbers, home addresses, and personal domains (e.g. `psford.com`) are credentials — never hardcoded in source committed to public repos. Use `example.com` in defaults, docs, and config templates. Real values belong in `.env` (gitignored) or environment variables only. Support/business emails created for a project are fine.
- Review SAST/DAST coverage when introducing new frameworks (SecurityCodeScan for C#, Bandit for Python).
- Hooks run automatically — if blocked, try to adjust; if stuck, ask Patrick.

# Git Flow (develop → main)

<!-- Canonical source: claude-env/shared/claude-md/git-flow-develop-main.md. -->
<!-- Branch names are parameterized: develop / main. -->
<!-- Repos that do not follow this flow (e.g. a single-trunk `master` model) should -->
<!-- omit this fragment and document their flow in CLAUDE.local.md. -->

## Critical Git Checkpoints

| Checkpoint | Rule | Enforcement |
|------------|------|-------------|
| **COMMITS** | Show status → diff → log → message → WAIT for explicit approval. A question is NOT approval. | Hook reminds; manual |
| **main BRANCH** | NEVER commit, merge, push --force, or rebase on `main`. | **BLOCKED** |
| **REVERSE MERGE** | NEVER merge `main` INTO `develop` (flow is `develop` → `main` only). | **BLOCKED** |
| **PR MERGE** | Patrick merges via GitHub web only — NEVER use `gh pr merge`. | **BLOCKED** |
| **MERGED PRs** | NEVER edit/push to merged/closed PRs. Always create a NEW PR. | **BLOCKED** |
| **NO RESET --HARD** | NEVER run `git reset --hard` (it destroyed uncommitted work once). Use `git merge`/`git rebase` to sync; `git stash` first if the tree is dirty. | **BLOCKED** |

## Branching Strategy

```
develop (work here) → PR → main (production)
                                  ↑
                           NEVER reverse this
```

- **Feature branches** for: new services, architecture changes, multi-file refactors, big UI changes, multi-session work, 5+ files.
- **Direct on `develop`** for: small fixes, tweaks, internal docs.
- **NEVER** commit directly to `main`, merge to it via CLI, deploy without an explicit "deploy", or click "Update branch" on the GitHub PR page.
- Before branching: `git fetch origin` and check `git log origin/main..develop` — never assume branches are in sync, and never offer to reuse the current branch without confirming it isn't `main`.

### Forbidden Operations (on develop)
| Operation | Why |
|-----------|-----|
| `git merge main` | `develop` flows TO `main` only |
| `git pull origin main` | Pulls and merges `main` into `develop` |
| `git rebase main` | Rewrites `develop` history based on `main` |

If the branches diverge, merge `develop` into `main` via PR — never the reverse.

## PR Rules

**Verification — when asked to check a PR:**
1. `git fetch origin` (ALWAYS fetch first).
2. `git log origin/main..develop --oneline` (ALWAYS `origin/main`, not local).
3. `gh pr view <N> --json commits` to see what's in the PR.
4. Report the delta — never just update PR title/body. Never assert PR state from memory; confirm with `gh pr view`.

**Merged PRs** — once merged/closed, a PR is DEAD. After any `git push`:
1. Check `gh pr list --head develop --base main --state open`.
2. No open PR → create a NEW one. Never reference old PR numbers without checking state. If Patrick is deploying, the previous PR is already merged — create a new PR for any follow-up fix.

## Pre-Commit Protocol

Before every commit, show Patrick:
1. `git status` — staged, unstaged, untracked
2. `git diff` — actual changes
3. `git log -3` — recent commits for style
4. Planned commit message
5. What will NOT happen (no `main`, no deploy, no PR)

Then **WAIT for explicit approval**. A question or comment resets the checkpoint — answer it, then wait again. Also verify: `claudeLog.md` updated, all files staged, feature tested.

# claude-env — project-specific

<!-- Project-specific rules for claude-env. The universal rules + git flow above -->
<!-- are assembled from claude-env/shared/claude-md/ by helpers/sync-claude-md.sh. -->
<!-- Edit THIS file (or the shared fragments) — never edit the generated CLAUDE.md. -->

Last verified: 2026-06-12

## About Claude-Env

**claude-env** is the isolated development-environment repository and the **source of truth for shared tooling and shared behavioral rules** across all companion repos. It contains:
- **Shared CLAUDE.md fragments** (`shared/claude-md/`) — the universal rules + git flow assembled into every repo's CLAUDE.md by `helpers/sync-claude-md.sh`.
- **Hooks** (`.claude/hooks/`) — enforced code quality, pre-commit/pre-push validation.
- **Helpers** (`helpers/`) — Python/PowerShell utilities for security, testing, deployment, Slack.
- **Infrastructure** (`infrastructure/`) — WSL2 setup contracts, Windows deployment pipeline, Azure/Bicep config.
- **Design docs** (`docs/`) — planning, retrospectives, audits (historical reference).

This repo is independent of app implementations. Companion repos consume its hooks and shared rules.

**Companion app repos:**
- `psford/stock-analyzer` — Stock analysis web application (.NET, Azure)
- `psford/road-trip` — Privacy-first geotagged photo map (.NET, Azure, MapLibre, iOS shell) — **live production app**
- `psford/photo-portfolio` — Photography portfolio (Astro + Cloudflare Workers + Azure Functions) — live
- `psford/whisper-service` — Speech-to-text Windows service (.NET)
- `psford/SysTTS` — Text-to-speech Windows service (.NET)
- `psford/T-Tracker` — Real-time MBTA tracker PWA (vanilla JS, Cloudflare Pages)
- `gpu-crash-analyzer`, `win-audio-analyzer` — Windows diagnostic utilities (PowerShell)

## Shared Knowledge Layer (how the rules above got here)

`CLAUDE.md` in every repo (including this one) is a **generated artifact**:
```
helpers/sync-claude-md.sh <repo>      # regenerate CLAUDE.md from fragments + CLAUDE.local.md
helpers/sync-claude-md.sh --check <repo>   # exit 3 if CLAUDE.md drifted (pre-commit/CI gate)
```
- Fragments live in `shared/claude-md/` (`00-universal.md`, `git-flow-develop-main.md`, `stack-*.md`).
- Each repo's `.claude/claude-md.json` lists which fragments it includes and supplies `{{VAR}}` values (branch names, etc.).
- Edit fragments (shared rules) or `CLAUDE.local.md` (project rules) — NEVER the generated `CLAUDE.md`.

## WSL2 Claude Code Sandbox

WSL2 provides an isolated Linux environment. See `infrastructure/wsl/CLAUDE.md` for setup contracts and environment-specific details. Hooks run in WSL2 and may detect the environment via `/proc/version`. claude-env itself has no app-specific environment requirements.

## Tooling Manifest (Public Contract)

`tooling-manifest.json` at the repo root is a **public contract** consumed by external bootstrap tooling (`psford/claude-mac-env` `setup.sh`). It catalogs the hooks and helpers this repo ships, classified into tiers (`always` / `universal` / `language` / `personal`) for tiered feature selection.

**Stable URL — do NOT move or rename:**
```
https://raw.githubusercontent.com/psford/claude-env/main/tooling-manifest.json
```
The path on `main` IS the contract. Renaming/moving/removing it breaks `claude-mac-env`'s bootstrap for all non-psford users. Any change to its location, top-level shape, or tier vocabulary must be coordinated with `claude-mac-env`.

**Maintenance:**
- `manifest_classification_guard.py` (pre-commit) detects new/changed files in `.claude/hooks/` and `helpers/`, classifies them by tier/language/feature, and proposes manifest entries for review.
- `manifest_completeness_guard.py` (pre-commit) BLOCKS commits that add files under `.claude/hooks/`, `helpers/`, or `helpers/hooks/` without a corresponding `tools[]` entry. Bypass with `MANIFEST_EXEMPT=1` only for genuinely-private utilities.

## Shared Tooling Index (for companion projects)

When you spot a pattern duplicated across 2+ repos, surface it here — don't quietly reinvent it per-project. Companion CLAUDE.local.md files should link back to these canonical entry points.

### Shared rules / CLAUDE.md
- `shared/claude-md/` + `helpers/sync-claude-md.sh` — the shared behavioral-rule fragments and the assembler. The canonical home for Principles, Git Flow, coding standards, verification discipline.

### Secrets and environment
- `infrastructure/wsl/pull-secrets.sh` — generic Azure Key Vault → `.env` generator (auto-detects vault, parametric).
- `helpers/load-env.sh` — env var loader.

### Plan authoring + execution
- `infrastructure/plan-templates/phase.md.template` — canonical phase plan template (Pre-Phase Sync Checklist, Prerequisites YAML, Done When checklist, dated Deferred Items table).
- `helpers/phase_preflight.py`, `helpers/phase_pr_check.py`, `helpers/validate_ac_coverage.py` — plan lifecycle helpers.

### Plan-quality enforcement hooks (PreToolUse, bypassable)
- `plan_branch_guard.py` (suppress per-line `<!-- BRANCH-OK: reason -->`), `defer_forever_guard.py` (`<!-- DEFER-PERMANENT: reason -->`), `engines_node_guard.py` (`ENGINES_NODE_OK=1`).

### Node / Playwright
- `helpers/install-playwright-wsl-browsers.sh` — Firefox/Webkit binary install on WSL2 with locked sudoers cage.

### Azure / endpoint patterns
- `azure_sp_identity_guard.py` — blocks Azure CLI ops when the logged-in SP doesn't match the repo's `.claude/azure-identity.json`.
- `endpoint_registry_guard.py` + `endpoint_schema_validator.py` — block hardcoded connection strings and validate `endpoints.json`. Activate when `endpoints.json` exists at a companion repo root.

## Hooks and Plugin Management

claude-env provides hooks consumed by companion repos:
- `.claude/hooks/` — pre-commit, pre-push, and CI hooks; shared read-only from claude-env.
- Each companion repo has its own `.claude/hooks/` directory (local hooks + wired claude-env hooks).

### Endpoint Registry Hooks (companion repos with `endpoints.json`)
- **`endpoint_registry_guard.py`** (PreToolUse/Bash) — blocks commits with hardcoded connection strings or direct `Environment.GetEnvironmentVariable()` for known endpoint keys. Activates only when `endpoints.json` exists at repo root.
- **`endpoint_schema_validator.py`** (PreToolUse/Bash) — validates `endpoints.json` structure on commits that modify endpoint files; rejects literal secrets in prod environments.

### Infrastructure and Cross-Repo Hooks
- **`cross_repo_fix_audit.py`** (PostToolUse/Bash) — fires after `fix:`/`fix!:` commits touching infra files; reminds to audit companion repos for the same issue.
- **`infra_commit_checklist.py`** (PreToolUse/Bash) — injects a categorized checklist before committing infra files (Bicep, GH Actions, Docker, auth/identity, appsettings.Production).
- **`bicep_infra_task_guard.py`** (PreToolUse/Bash) — blocks plan-phase commits referencing Bicep/KeyVault/RBAC without a deployment task. Bypass `<!-- INFRA-DEPLOY-OK: reason -->`.
- **`azure_sp_identity_guard.py`** (PreToolUse/Bash) — blocks Azure CLI ops when the logged-in SP mismatches `.claude/azure-identity.json`.

## Companion-repo bootstrap

Bootstrapping / re-syncing a companion repo:
1. Add `.claude/claude-md.json` listing the repo's fragments (`00-universal`, optionally `git-flow-develop-main`, optionally a `stack-*`) and `vars`.
2. Move project-specific content into `CLAUDE.local.md`.
3. Run `helpers/sync-claude-md.sh <repo>` to generate `CLAUDE.md`.
4. Wire the claude-env hooks the repo needs into its `.claude/hooks/` + settings.
A `--check` run in CI/pre-commit keeps the generated `CLAUDE.md` from drifting.

## Project Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | **Generated** — assembled from `shared/claude-md/` + `CLAUDE.local.md`. Do not edit directly. |
| `CLAUDE.local.md` | claude-env's project-specific rules (this file). |
| `shared/claude-md/` | Shared behavioral-rule fragments for all repos. |
| `helpers/sync-claude-md.sh` | Assembler that generates each repo's CLAUDE.md. |
| `sessionState.md` | Current session context. |
| `claudeLog.md` | Action log. |
| `helpers/` | Python/PowerShell utilities. |
| `infrastructure/wsl/CLAUDE.md` | WSL2 sandbox setup contracts. |
| `infrastructure/windows-deploy/CLAUDE.md` | Windows deployment pipeline contracts. |
| `.claude/hooks/` | Hooks enforcing code quality and repo hygiene. |
| `tooling-manifest.json` | Public contract: catalog of hooks/helpers for external bootstrap. |
| `.env` | API keys and secrets — not committed. |
