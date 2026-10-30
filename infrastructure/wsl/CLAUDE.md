# WSL2 Claude Code Sandbox

Last verified: 2026-06-08

## Purpose

Isolated Linux environment for Claude Code to develop, build, and test .NET / Python / Node projects without risking the broader Windows filesystem or configuration. The sandbox is enforced by OS-level mechanisms (WSL interop disabled, sudoers password-gated, `/etc` files immutable), not by convention or prompt directives.

**Threat model: Claude itself.** The cage assumes any process running as user `patrick` may attempt to escape. Containment must come from the kernel + sudoers + ext4 immutable bit, never from "Claude follows the rules."

## Contracts

- **Exposes**: Setup scripts that produce a fully configured Ubuntu distro with .NET 8, Python 3, Node.js, SQL tools, Blender 5.2 LTS with the Blender Lab MCP server (user space, `install-blender.sh`), and gitleaks (user space, `install-gitleaks.sh`), plus a security cage that converts the read-only filesystem mount and sudo policy from convention to enforcement.
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
- **Blender in user space, on the GPU through Mesa d3d12 + X11**: `install-blender.sh` puts the official tarball and the Blender Lab MCP relay under `~/.local/opt`, so it needs no sudo. The GPU reaches Linux only as DirectX 12 (`/dev/dxg`), so Blender's OpenGL goes through Mesa's d3d12 driver (`GALLIUM_DRIVER=d3d12`). Ubuntu's Mesa ships no dzn Vulkan driver, so the Vulkan backend would land on lavapipe (CPU).
  - **Two traps.** The d3d12 driver defaults to the CPU's integrated Radeon, so `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` pins it to the RTX 4090. And Blender's Wayland window on d3d12 makes WSLg drop the connection ("The Wayland connection broke"), after which Mesa segfaults during exit. Unsetting `WAYLAND_DISPLAY` doesn't help, because libwayland falls back to `wayland-0`; pointing it at a socket that doesn't exist makes Blender fall back to X11.
  - The `~/.local/bin/blender` launcher sets all three, so every caller gets the GPU, including the MCP server's `*_for_cli` tools.
  - Side effect: Blender's front-buffer readback (window and area screenshots) returns black; renders are unaffected.
  - Driving a Windows Blender over TCP instead would run Claude-written Python outside the cage, so that path is closed by design.

## Key Files

- `wsl-setup.sh` -- Main setup script (idempotent). Configures wsl.conf, fstab carve-out, installs packages.
- `harden-wsl.sh` -- Security cage installer (Patrick runs, requires password). Disables interop, installs sudoers cage, sets chattr +i.
- `verify-cage.sh` -- Non-destructive cage verification. Runs every known bypass attempt with benign targets; all must fail.
- `install-blender.sh` -- Blender LTS + the Blender Lab MCP add-on and relay, in user space, with pinned versions and checksums; registers the relay with Claude Code at user scope (idempotent; called by `wsl-setup.sh`). Rules for using it: `shared/claude-md/stack-3d-design.md`.
- `install-gitleaks.sh` -- gitleaks to `~/.local/bin`, pinned version, sha256 checked against the release's checksums file (idempotent; called by `wsl-setup.sh`, checked by `verify-setup.sh`). The `~/.claude` Stop hook needs it, and commits nothing without it.
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
- **Playwright system deps require the `wsl.exe --user root` carve-out**: the cage's locked sudoers blocks `playwright install-deps` from running apt-get. The browser binaries themselves install fine from inside the cage (`npx playwright install firefox webkit`), but Firefox/Webkit need apt packages (libnspr4, libnss3, libdbus-glib-1-2, libenchant-2-2, libhyphen0, libsecret-1-0, libwoff1, libGLESv2, etc.) that must be installed as root. Use `claude-env/helpers/install-playwright-wsl-browsers.sh` — it downloads binaries from inside WSL then prints the exact `wsl.exe --user root` command for the operator to paste into a Windows PowerShell terminal. This is the same root-carve-out documented in **Recovery** above, applied to a non-recovery one-time setup.
