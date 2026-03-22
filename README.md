# Claude-Env

**Claude-Env** is a standalone development environment repository containing reusable tooling, hooks, and helpers for Claude Code sessions.

This repo is **independent of app implementations** and used as a foundation by companion app repos via bootstrap scripts.

## What's Inside

### Hooks (`.claude/hooks/`)

Enforced code quality and compliance:
- `block_main_commits.py` — Prevent direct commits to main branch
- `check_log_sanitization.py` — Enforce CWE-117 log sanitization in C#
- `commit_atomicity_guard.py` — Ensure commits are logically atomic
- `eodhd_rebuild_guard.py` — Remind to rebuild WPF apps after code changes
- `ef_migration_guard.py` — Enforce EF Core migrations over raw SQL
- `jenkins_pre_push.py` — Integrate with Jenkins CI
- `merged_pr_guard.py` — Prevent edits to merged/closed PRs
- `check_responsive_tests.py` — Validate responsive design testing
- `check_md_table_totals.py` — Validate table calculations in docs
- Other specialized hooks for compliance

### Helpers (`helpers/`)

Python and shell utilities:
- **Testing**: `ui_test.py`, `responsive_test.py`, `interactive_test.py`
- **Security**: `security_scan.py` (Bandit), `zap_scan.py` (OWASP ZAP)
- **Documentation**: `check_links.py`, `test_docs_tabs.py`
- **Assets**: `generate_favicon.py`, `generate_solid_icons.py`, `generate_stream_deck_icons.py`
- **Slack Integration**: `slack_bot.py`, `slack_listener.py`, `slack_acknowledger.py`
- **Utilities**: `archive_logs.py`, `checkpoint.py`, `load-env.sh`

### Infrastructure (`infrastructure/`)

Setup and deployment:
- **WSL2 Setup** (`infrastructure/wsl/`):
  - `wsl-setup.sh` — Configure Ubuntu WSL2 with .NET, Python, Node.js, SQL tools (idempotent)
  - `pull-secrets.sh` — Fetch secrets from Azure Key Vault into `.env`
  - `verify-setup.sh` — Verify all components are installed and configured
  - `populate-keyvault.ps1` — One-time: store secrets in Key Vault (Windows only)

### Docs (`docs/`)

Planning, retrospectives, and historical reference:
- `design-plans/` — Architecture and feature design documents
- `retrospectives/` — Session retrospectives and lessons learned
- `test-plans/` — Test strategies for major features
- `implementation-plans/` — Step-by-step implementation guides

## Companion App Repos

This environment is used by:

- **[psford/stock-analyzer](https://github.com/psford/stock-analyzer)** — Stock analysis web application (.NET)
- **[psford/road-trip](https://github.com/psford/road-trip)** — Road trip photo mapping app (future)
- Other projects may bootstrap from this environment

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

3. **Use with an app repo:** Clone the app repo (e.g., stock-analyzer) and it will reference hooks and helpers from claude-env.

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
| `CLAUDE.md` | Instructions and guidelines for Claude Code sessions |
| `sessionState.md` | Current session context |
| `claudeLog.md` | Action log from previous sessions |
| `.claude/hooks/` | Git hooks enforcing code quality |
| `helpers/` | Utility scripts (testing, deployment, security, Slack) |
| `infrastructure/wsl/` | WSL2 sandbox setup and configuration |
| `docs/` | Design plans, retrospectives, test plans |

## Git Flow

```
develop (work here) → PR → main (production)
                      ↑
               NEVER reverse this
```

- **Direct commits** to develop for small fixes and tweaks
- **Feature branches** for: new services, major refactors, multi-session work
- **PR required** for main (CI must pass, Patrick reviews)
- **NEVER** commit directly to main, merge to main via CLI, or use `git rebase main`

## Principles

- **Rules are hard blocks** — Hooks enforce checkpoints automatically
- **Do it yourself** — Work autonomously, only escalate for commit/deploy approval
- **Verify before claiming** — Run tests, build, lint — show evidence before reporting success
- **Fix immediately** — No technical debt; fix deprecated code and suboptimal patterns now
- **Challenge bad practices** — Push back against security issues and poor design

## Security

- **Personal identifiers are secrets** — Never hardcode personal emails, phone numbers, domains in source
- **Log sanitization** — All user strings in C# logs wrapped in `LogSanitizer.Sanitize()` (CWE-117)
- **Hooks run automatically** — If blocked, try to adjust; if stuck, ask Patrick

## License

MIT License - see LICENSE for details.
