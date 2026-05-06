# WSL2 Claude Code Sandbox

Last verified: 2026-05-05

## Purpose

Isolated Linux environment for Claude Code to develop, build, and test .NET / Python / Node projects without risking the broader Windows filesystem or configuration. The sandbox is enforced by OS-level mechanisms (WSL interop disabled, sudoers password-gated, `/etc` files immutable), not by convention or prompt directives.

**Threat model: Claude itself.** The cage assumes any process running as user `patrick` may attempt to escape. Containment must come from the kernel + sudoers + ext4 immutable bit, never from "Claude follows the rules."

## Contracts

- **Exposes**: Setup scripts that produce a fully configured Ubuntu distro with .NET 8, Python 3, Node.js, and SQL tools, plus a security cage that converts the read-only filesystem mount and sudo policy from convention to enforcement.
- **Guarantees**:
  - `wsl-setup.sh` is idempotent (safe to re-run)
  - Windows filesystem mounted read-only (`/mnt/c`, `/mnt/d`) by default
  - **Writable carve-out**: `C:\Users\patri\Documents\claudeProjects\projects` is mounted `rw` at `/mnt/c/Users/patri/Documents/claudeProjects/projects` via `/etc/fstab`. This is the bridge: Claude develops in WSL, drops finished projects into the carve-out, runs them natively on Windows. Everything else under `/mnt/c` stays read-only. <!-- # STALE-PATH-OK: this is the literal contract path the cage protects -->

  - **WSL->Windows interop disabled**: `[interop] enabled=false` in `/etc/wsl.conf`. `powershell.exe`, `cmd.exe`, `wsl.exe`, and any `/mnt/c/Windows/*.exe` cannot be executed from inside the WSL distro.
  - **Sudo password-gated**: `/etc/sudoers.d/zz-claude-cage` requires patrick's password for every sudo invocation outside a tiny NOPASSWD allowlist (read-only diagnostics: journalctl, dmesg, systemctl status/is-active/is-enabled).
  - **`/etc` files immutable**: `chattr +i` set on `/etc/wsl.conf`, `/etc/fstab`, `/etc/sudoers`. Even root cannot modify these without first removing the immutable flag (which itself requires a password-gated sudo).
  - Windows PATH excluded (`appendWindowsPath=false`)
  - Secrets pulled from Azure Key Vault into `.env` (never stored in scripts)
  - SQL logins: `wsl_claude` (read/write), `wsl_claude_admin` (DDL for migrations)
- **Expects**: Fresh Ubuntu WSL2 distro, Azure CLI authenticated on Windows, SQL Express with TCP enabled on Windows. The user must manually run `harden-wsl.sh` (typing their password) after `wsl-setup.sh` to install the cage.

## Dependencies

- **Uses**: Azure Key Vault (secrets), Windows SQL Express (TCP port 1433), Windows filesystem (read-only by default with carve-out)
- **Used by**: Claude Code sessions running in WSL2
- **Boundary**: These scripts configure the WSL2 environment only. They do not modify Windows, Azure resources, or application code.

## Key Decisions

- **OS-level enforcement, not policy**: The sandbox boundary is enforced by kernel + sudoers + ext4 immutable bit, not by CLAUDE.md rules or hooks. Hooks can be edited; rules can be ignored. Kernel rejections cannot. Every layer assumes Claude will try to bypass.
- **Read-only automount with single rw carve-out**: System-wide `options=metadata,ro` in `wsl.conf` blocks all writes to `/mnt/c` and `/mnt/d`. A single `drvfs rw` mount in `/etc/fstab` re-exposes the projects folder as writable. Cross-platform utilities (PowerShell scripts, .NET tools) are written in WSL, land in the carve-out, and run natively on Windows.
- **Interop fully off, not partially**: `[interop] enabled=false` blocks all Windows binary execution from inside WSL. Patrick's workflow already runs Windows utilities natively on Windows (taskbar/icon launches), so the boundary costs nothing functional. Patrick's own `code .`-from-WSL workflow is unaffected because VS Code Remote-WSL boots from the Windows side.
- **Cage installation is one-way**: `harden-wsl.sh` is on the honor system the first time (passwordless sudo lets Claude install it too). Once installed, undoing it (chattr -i, sudoers edit, wsl.conf edit) requires patrick's password. Claude (running as patrick) cannot uninstall.
- **Sudoers filename `zz-claude-cage`**: Sudoers files in `/etc/sudoers.d/` are loaded in lexical order; ASCII puts digits BEFORE letters, so a `99-` prefix is NOT last when other files use letter prefixes (e.g. the WSL-default `/etc/sudoers.d/patrick`). The `zz-` prefix guarantees last-match-wins regardless of other entries.
- **Why fstab + mountFsTab=true**: WSL's automount processes fstab when `mountFsTab=true`. The fstab entry layers a fresh `drvfs` mount over the ro automount path, so the kernel resolves the rw mount when entering the carve-out subtree.
- **Azure Key Vault for secrets**: `pull-secrets.sh` fetches credentials at session start; no secrets in git
- **Two SQL logins**: Least-privilege separation -- `wsl_claude` for runtime, `wsl_claude_admin` for migrations only

## Key Files

- `wsl-setup.sh` -- Main setup script (idempotent). Configures wsl.conf, fstab carve-out, installs packages.
- `harden-wsl.sh` -- Security cage installer (Patrick runs, requires password). Disables interop, installs sudoers cage, sets chattr +i.
- `verify-cage.sh` -- Non-destructive cage verification. Runs every known bypass attempt with benign targets; all must fail.
- `pull-secrets.sh` -- Fetches secrets from Key Vault into `.env`
- `populate-keyvault.ps1` -- One-time: stores secrets in Key Vault (run on Windows)
- `script-audit.md` -- Audit of all PS1 scripts for WSL2 compatibility

## Setup Flow

1. From Windows PowerShell: `wsl --install Ubuntu-24.04` (if not already installed)
2. From WSL bash: `bash wsl-setup.sh` (installs packages, configures carve-out)
3. From Windows PowerShell: `wsl --shutdown` (apply wsl.conf + fstab changes)
4. From WSL bash: `bash harden-wsl.sh` (Patrick types `YES` and password; installs cage)
5. From Windows PowerShell: `wsl --shutdown` (apply interop=false)
6. From WSL bash: `bash verify-cage.sh` (all bypass attempts must fail)
7. One-time manual: `sudo lsattr /etc/sudoers` should show `----i---` (verify-cage.sh cannot do this from patrick's user because /etc/sudoers is mode 0440)

## Gotchas

- **`wsl --shutdown` required twice in setup**: once after `wsl-setup.sh` (for wsl.conf/fstab), once after `harden-wsl.sh` (for interop=false)
- If the carve-out path appears read-only, check: `mount | grep claudeProjects` should show `rw,...,aname=drvfs;path=C:\Users\patri\...`. If the line is missing, fstab didn't process — verify `mountFsTab=true` in `/etc/wsl.conf` and that the path on the Windows side actually exists
- **Recovery**: if the cage locks Patrick out (e.g., forgotten password, broken sudoers config), boot as root from Windows: `wsl -d Ubuntu-24.04 -u root`. Root login bypasses sudoers entirely. From there: `chattr -i /etc/<file>`, edit, `chattr +i` again, or `passwd patrick` to reset.
- **Verify-cage tests are non-destructive by design**: every "block" test uses benign targets (`/dev/null`, nonexistent files) so even if a layer breaks, no state damage occurs. Earlier versions ran destructive commands and dismantled the cage when it didn't hold.
- **/etc/sudoers chattr +i is not patrick-observable**: file mode is 0440 (root-only), so `lsattr` from patrick returns "Permission denied". Verify manually with `sudo lsattr /etc/sudoers` once after install.
- Cannot rebuild WPF applications from WSL2 (requires Windows)
- SQL Express TCP must be manually enabled in SQL Server Configuration Manager on Windows
