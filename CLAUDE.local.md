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

A shared rule reaches a repo one of two ways, and which one depends on whether
the fragment has anything per-repo in it.

**A fragment with no `{{VARS}}` is linked, not copied.** It is byte-identical
everywhere, so it lives in exactly one file and each repo gets a relative
symlink at `.claude/rules/<name>.md`. Claude Code reads that directory as
memory. There is no second copy, so there is nothing to fall out of line —
which is the point: eleven repos once held eleven copies and nothing compared
them.

**A fragment with `{{VARS}}` is generated into `CLAUDE.md`.** A symlink cannot
turn `{{TRUNK_BRANCH}}` into `master`. `git-flow-trunk` is the only fragment
left in this category, because its two consumers genuinely disagree —
T-Tracker's trunk is `master`, photo-portfolio's is `main`.

`git-flow-develop-main` used to be here too and is not any more (CE-5.6): all
eight repos using it were `develop` / `main`, so the variable had exactly one
value and was the only thing keeping those repos on a copy of their git-flow
rules. Its branch names are literal now, so it links like the rest. A different
two-branch layout needs a new fragment rather than the variable back.

```
helpers/sync-claude-md.sh <repo>           # write the links, regenerate CLAUDE.md
helpers/sync-claude-md.sh --check <repo>   # exit 3 if a link is missing, dangling,
                                           # misdirected, or CLAUDE.md drifted
```

- Fragments live in `shared/claude-md/` (`00-universal.md`,
  `git-flow-develop-main.md`, `stack-*.md`).
- Each repo's `.claude/claude-md.json` lists its fragments and supplies
  `{{VAR}}` values.
- Edit fragments (shared rules) or `CLAUDE.local.md` (project rules) — NEVER
  the generated `CLAUDE.md`, and never a file under `.claude/rules/`, which is
  the shared fragment itself seen through a link.

**Links are relative**, so claude-env must sit beside every consuming repo.
claude-env is its own exception: its link stays inside the repo. A checkout
without that sibling fails loudly (`--check` exit 3) rather than silently
inheriting nothing.

Drift is no longer the way inheritance fails. **Absence is**, and it is quieter
— a repo with a dangling link looks exactly like a healthy one.

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
