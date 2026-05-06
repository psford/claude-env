# WSL2 Claude Code Sandbox

Last verified: 2026-05-05

## Purpose

Isolated Linux environment for Claude Code to develop, build, and test .NET / Python / Node projects without risking the broader Windows filesystem or configuration. Windows mount is read-only by default with a single writable carve-out for the cross-platform projects folder, so Claude can hand finished work over to Windows / Mac / Azure runtimes without being able to clobber host files.

## Contracts

- **Exposes**: Setup scripts that produce a fully configured Ubuntu distro with .NET 8, Python 3, Node.js, and SQL tools
- **Guarantees**:
  - `wsl-setup.sh` is idempotent (safe to re-run)
  - Windows filesystem mounted read-only (`/mnt/c`, `/mnt/d`) by default
  - **Writable carve-out**: `C:\Users\patri\Documents\claudeProjects\projects` is mounted `rw` at `/mnt/c/Users/patri/Documents/claudeProjects/projects` via `/etc/fstab`. This is the bridge: Claude develops in WSL, drops finished projects into the carve-out, runs them natively on Windows. Everything else under `/mnt/c` stays read-only.
  - Windows PATH excluded (`appendWindowsPath=false`)
  - Secrets pulled from Azure Key Vault into `.env` (never stored in scripts)
  - SQL logins: `wsl_claude` (read/write), `wsl_claude_admin` (DDL for migrations)
- **Expects**: Fresh Ubuntu WSL2 distro, Azure CLI authenticated on Windows, SQL Express with TCP enabled on Windows

## Dependencies

- **Uses**: Azure Key Vault (secrets), Windows SQL Express (TCP port 1433), Windows filesystem (read-only)
- **Used by**: Claude Code sessions running in WSL2
- **Boundary**: These scripts configure the WSL2 environment only. They do not modify Windows, Azure resources, or application code.

## Key Decisions

- **Read-only automount with single rw carve-out**: System-wide `options=metadata,ro` in `wsl.conf` blocks all writes to `/mnt/c` and `/mnt/d`. A single `drvfs rw` mount in `/etc/fstab` re-exposes the projects folder as writable. This gives Claude a development->runtime bridge without granting global Windows write access. Cross-platform utilities (PowerShell scripts, .NET tools) are written in WSL, land in the carve-out, and run natively on Windows.
- **Why fstab + mountFsTab=true**: WSL's automount processes fstab when `mountFsTab=true`. The fstab entry layers a fresh `drvfs` mount over the ro automount path, so the kernel resolves the rw mount when entering the carve-out subtree.
- **Azure Key Vault for secrets**: `pull-secrets.sh` fetches credentials at session start; no secrets in git
- **Two SQL logins**: Least-privilege separation -- `wsl_claude` for runtime, `wsl_claude_admin` for migrations only

## Key Files

- `wsl-setup.sh` -- Main setup script (idempotent)
- `pull-secrets.sh` -- Fetches secrets from Key Vault into `.env`
- `populate-keyvault.ps1` -- One-time: stores secrets in Key Vault (run on Windows)
- `script-audit.md` -- Audit of all PS1 scripts for WSL2 compatibility

## Gotchas

- `wsl --shutdown` required after first `wsl-setup.sh` run (wsl.conf changes need restart)
- `wsl --shutdown` also required after fstab carve-out is added or path changes — the live mount survives the current session, but persistence depends on the fstab entry being processed at boot
- If the carve-out path appears read-only, check: `mount | grep claudeProjects` should show `rw,...,aname=drvfs;path=C:\Users\patri\...`. If the line is missing, fstab didn't process — verify `mountFsTab=true` in `/etc/wsl.conf` and that the path on the Windows side actually exists
- Cannot rebuild WPF applications from WSL2 (requires Windows)
- SQL Express TCP must be manually enabled in SQL Server Configuration Manager on Windows
