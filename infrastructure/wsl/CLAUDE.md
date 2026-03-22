# WSL2 Claude Code Sandbox

Last verified: 2026-03-21

## Purpose

Isolated Linux environment for Claude Code to develop, build, and test .NET projects without risking Windows filesystem or configuration. Read-only Windows mount prevents accidental modification of host files.

## Contracts

- **Exposes**: Setup scripts that produce a fully configured Ubuntu distro with .NET 8, Python 3, Node.js, and SQL tools
- **Guarantees**:
  - `wsl-setup.sh` is idempotent (safe to re-run)
  - Windows filesystem mounted read-only (`/mnt/c`, `/mnt/d`)
  - Windows PATH excluded (`appendWindowsPath=false`)
  - Secrets pulled from Azure Key Vault into `.env` (never stored in scripts)
  - SQL logins: `wsl_claude` (read/write), `wsl_claude_admin` (DDL for migrations)
- **Expects**: Fresh Ubuntu WSL2 distro, Azure CLI authenticated on Windows, SQL Express with TCP enabled on Windows

## Dependencies

- **Uses**: Azure Key Vault (secrets), Windows SQL Express (TCP port 1433), Windows filesystem (read-only)
- **Used by**: Claude Code sessions running in WSL2
- **Boundary**: These scripts configure the WSL2 environment only. They do not modify Windows, Azure resources, or application code.

## Key Decisions

- **Read-only automount**: Prevents Claude from modifying Windows files; VS Code Remote-WSL still works for editing
- **Azure Key Vault for secrets**: `pull-secrets.sh` fetches credentials at session start; no secrets in git
- **Two SQL logins**: Least-privilege separation -- `wsl_claude` for runtime, `wsl_claude_admin` for migrations only

## Key Files

- `wsl-setup.sh` -- Main setup script (idempotent)
- `pull-secrets.sh` -- Fetches secrets from Key Vault into `.env`
- `populate-keyvault.ps1` -- One-time: stores secrets in Key Vault (run on Windows)
- `script-audit.md` -- Audit of all PS1 scripts for WSL2 compatibility

## Gotchas

- `wsl --shutdown` required after first `wsl-setup.sh` run (wsl.conf changes need restart)
- Cannot rebuild WPF applications from WSL2 (requires Windows)
- SQL Express TCP must be manually enabled in SQL Server Configuration Manager on Windows
