# Claude-Env

**Claude-Env** is a standalone development-environment repository and the **source of truth for shared tooling and shared behavioral rules** across Patrick's companion app repos: reusable hooks, helpers, infrastructure setup, and the shared `CLAUDE.md` rule set every companion repo is generated from.

This repo is **independent of app implementations** and used as a foundation by companion app repos via bootstrap scripts.

## Shared CLAUDE.md Knowledge Layer

Every companion repo's `CLAUDE.md` is a **generated artifact**, assembled from fragments here plus that repo's own private rules — so a behavioral rule fixed once propagates everywhere instead of drifting per-repo.

- `shared/claude-md/` — shared rule fragments (`00-universal.md`, `git-flow-develop-main.md`, `git-flow-trunk.md`, `stack-*.md`)
- `helpers/sync-claude-md.sh <repo>` — regenerates a repo's `CLAUDE.md` from its `.claude/claude-md.json` (which lists included fragments + template vars) and its `CLAUDE.local.md`
- `helpers/sync-claude-md.sh --check <repo>` — exits non-zero if a repo's `CLAUDE.md` has drifted from its fragments; wired as a pre-commit/CI gate

Edit fragments (or a repo's `CLAUDE.local.md`) — never a generated `CLAUDE.md` directly.

The full, current rule set (behavioral checkpoints, principles, coding standards, git flow) lives in [`shared/claude-md/00-universal.md`](shared/claude-md/00-universal.md) and this repo's own generated [`CLAUDE.md`](CLAUDE.md) — not duplicated here, so it can't drift out of sync with what's actually enforced.

## What's Inside

### Hooks (`.claude/hooks/`)

60+ hooks enforcing code quality, git-flow discipline, plan/design integrity, and deploy safety — pre-commit, pre-push, and PreToolUse/PostToolUse guards for Claude Code sessions. Organized by domain (git flow, CI cost control, plan staleness, endpoint/secret hygiene, infra change checklists, and more). The current, authoritative catalog is [`tooling-manifest.json`](tooling-manifest.json) — see below.

### Helpers (`helpers/`)

Python and shell utilities:
- **Testing**: `ui_test.py`, `responsive_test.py`, `interactive_test.py`, `test_hover_images.py`
- **Security**: `security_scan.py` (Bandit), `zap_scan.py` (OWASP ZAP)
- **Documentation**: `check_links.py`, `test_docs_tabs.py`
- **Shared CLAUDE.md**: `sync-claude-md.sh`
- **Plan lifecycle**: `phase_preflight.py`, `phase_pr_check.py`, `validate_ac_coverage.py`, `park-work.sh`, `deploy-gate.sh`
- **Assets**: `generate_favicon.py`, `generate_solid_icons.py`, `generate_stream_deck_icons.py`
- **Slack Integration**: `slack_bot.py`, `slack_listener.py`, `slack_acknowledger.py`, `slack_notify.py`
- **Utilities**: `archive_logs.py`, `checkpoint.py`, `load-env.sh`

### Tooling Manifest (`tooling-manifest.json`)

A **public contract** cataloging every hook and helper in this repo, classified into tiers (`always` / `universal` / `language` / `personal`) for tiered bootstrap selection. Consumed externally by `psford/claude-mac-env`'s `setup.sh` at a stable pinned URL:

```
https://raw.githubusercontent.com/psford/claude-env/main/tooling-manifest.json
```

Adding a hook or helper without a manifest entry is blocked by `manifest_completeness_guard.py` (pre-commit).

### Infrastructure (`infrastructure/`)

Setup and deployment:
- **WSL2 Setup** (`infrastructure/wsl/`): `wsl-setup.sh` (idempotent Ubuntu WSL2 setup — .NET, Python, Node.js, SQL tools), `pull-secrets.sh` (Azure Key Vault → `.env`), `verify-setup.sh`, `populate-keyvault.ps1` (one-time, Windows only)
- **Bicep** (`infrastructure/bicep/`): shared Azure infrastructure modules (Key Vault, etc.) consumed by companion repos
- **Bootstrap** (`infrastructure/bootstrap/`): companion-repo onboarding scripts
- **Windows Deploy** (`infrastructure/windows-deploy/`): Windows app deployment pipeline contracts

### Docs (`docs/`)

Planning, retrospectives, and historical reference — `design-plans/`, `implementation-plans/`, `retrospectives/`, `test-plans/`, `runbooks/`, `security-issues/`, `diagrams/`, `templates/`.

## Companion App Repos

This environment is used by:

- **[psford/road-trip](https://github.com/psford/road-trip)** — Privacy-first geotagged photo map (.NET, Azure, MapLibre, iOS shell) — **live production**
- **[psford/photo-portfolio](https://github.com/psford/photo-portfolio)** — Photography portfolio (Astro + Cloudflare Workers + Azure Functions) — **live**
- **[psford/stock-analyzer](https://github.com/psford/stock-analyzer)** — Stock analysis web application (.NET, Azure)
- **[psford/T-Tracker](https://github.com/psford/T-Tracker)** — Real-time MBTA tracker PWA (vanilla JS, Cloudflare Pages)
- **[psford/whisper-service](https://github.com/psford/whisper-service)** — Speech-to-text Windows service (.NET)
- **[psford/SysTTS](https://github.com/psford/SysTTS)** — Text-to-speech Windows service (.NET)
- **gpu-crash-analyzer**, **win-audio-analyzer** — Windows diagnostic utilities (PowerShell)

## Quick Start

### For App Development

1. **Clone claude-env:**
   ```bash
   git clone https://github.com/psford/claude-env.git
   cd claude-env
   ```

2. **Install hooks** (run once):
   ```bash
   ./scripts/install-hooks.sh
   ```

3. **Bootstrap a companion repo** onto the shared knowledge layer:
   ```bash
   # In the companion repo: add .claude/claude-md.json (fragments + vars), then
   ./helpers/sync-claude-md.sh <repo-path>
   ```
   The companion repo's own `.claude/hooks/` wires in whichever claude-env hooks it needs.

### For WSL2 Setup (Windows developers)

1. **Create fresh Ubuntu WSL2 distro:**
   ```bash
   wsl --list --verbose
   wsl --install Ubuntu
   ```

2. **Run setup script:**
   ```bash
   cd /mnt/c/Users/YourUser/path/to/claude-env
   bash infrastructure/wsl/wsl-setup.sh
   ```

3. **Fetch secrets** (after authenticating to Azure):
   ```bash
   bash infrastructure/wsl/pull-secrets.sh
   ```

4. **Verify setup:**
   ```bash
   bash infrastructure/wsl/verify-setup.sh
   ```

## Key Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | **Generated** — assembled from `shared/claude-md/` + `CLAUDE.local.md`; the full current rule set |
| `CLAUDE.local.md` | claude-env's own project-specific rules |
| `shared/claude-md/` | Shared behavioral-rule fragments consumed by every companion repo |
| `tooling-manifest.json` | Public contract: catalog of hooks/helpers for external bootstrap |
| `ROADMAP.md` | Cross-project roadmap (items spanning multiple repos) |
| `sessionState.md` | Current session context |
| `claudeLog.md` | Action log from previous sessions |
| `.claude/hooks/` | Git hooks enforcing code quality and process discipline |
| `helpers/` | Utility scripts (testing, deployment, security, Slack, plan lifecycle) |
| `infrastructure/` | WSL2 setup, Bicep modules, Windows deploy pipeline |
| `docs/` | Design plans, retrospectives, runbooks, test plans |

## Git Flow

```
develop (work here) → PR → main (production)
                      ↑
               NEVER reverse this
```

- **Direct commits** to develop for small fixes and tweaks
- **Feature branches** for: new services, major refactors, multi-session work
- **PR required** for main (CI must pass, Patrick reviews and merges via the GitHub web UI — never `gh pr merge`)
- **NEVER** commit directly to main, merge to main via CLI, or use `git rebase main`

This is the default flow (`git-flow-develop-main.md`); some repos instead use a trunk-based fragment (`git-flow-trunk.md`) where it's a better fit.

## Principles

The full, current set of behavioral checkpoints and principles lives in [`shared/claude-md/00-universal.md`](shared/claude-md/00-universal.md) (rendered into every repo's `CLAUDE.md`) — not duplicated here to avoid drift. A few load-bearing ones:

- **Rules are hard blocks** — Hooks enforce checkpoints automatically; they fail, never warn-and-pass
- **Diagnose before fix** — Root-cause first (inspect, measure, log); never guess
- **Do it yourself** — Work autonomously, only escalate for commit/deploy approval
- **Verify before claiming** — Every "done" needs an exact command + real output, labeled by provenance
- **Audit the class** — A bug found in one place gets searched for everywhere else it could recur
- **Don't freelance the design** — Implementation executes the agreed design; a second workaround is a stop signal, not a green light

## Security

- **Personal identifiers are secrets** — Never hardcode personal emails, phone numbers, domains in source
- **Log sanitization** — All user strings in logs wrapped in sanitization wrappers where applicable (CWE-117)
- **Hooks run automatically** — If blocked, try to adjust; if stuck, ask Patrick

## License

MIT License - see LICENSE for details.
