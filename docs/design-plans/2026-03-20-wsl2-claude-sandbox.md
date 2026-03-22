# WSL2 Claude Code Sandbox Design

## Summary

This document describes a development environment configuration that runs Claude Code — Anthropic's AI coding assistant CLI — inside a WSL2 Ubuntu instance on the existing Windows 11 machine. The core motivation is that Claude Code's permission system is per-command on Windows, which means every unfamiliar shell command triggers an interactive approval prompt that blocks automated multi-step work. By running Claude inside a Linux environment where `Bash(*)` can be granted as a single blanket permission, all subagent activity becomes prompt-free while safety is preserved through hook scripts that block destructive operations at the git and shell level.

The setup isolates WSL2 completely from the Windows filesystem by disabling drive automounting, so the worst-case outcome of an errant Claude command is a trashed Linux distro — recoverable in under 15 minutes by re-running a setup script. The Windows environment (VS Code, SQL Express, the EodhdLoader WPF app) remains unchanged and continues to operate independently. Claude accesses the shared SQL Express database over TCP via WSL2's mirrored networking mode, and API secrets are fetched from Azure Key Vault rather than copied from Windows, so no credentials ever touch the Linux filesystem directly. Claude's own state — memory files, plugin manifests, and settings — is stored in a private git repository and restored automatically on rebuild.

## Definition of Done

1. **Claude Code runs in WSL2** with `Bash(*)` permissions — zero permission prompts for any command, including subagents.
2. **Windows filesystem is isolated** — no Windows drives mounted. Claude cannot read or write any Windows files.
3. **VS Code works via Remote-WSL** — normal IDE experience, same as current Windows setup.
4. **Full dev toolchain in WSL2** — .NET 8 SDK, Python 3, Node.js, Azure CLI. Build, test, and commit entirely within WSL2.
5. **Database connectivity** — WSL2 connects to Windows SQL Express via TCP (mirrored networking). EodhdLoader on Windows continues using named pipes.
6. **Disposable environment** — if Claude destroys the WSL2 filesystem, a setup script rebuilds it in ~10 minutes from git repos.
7. **State preserved across rebuilds** — `~/.claude/` (settings, memory, plugins) backed up in a private git repo. Secrets stored on Windows, copied during setup.
8. **Parallel with current setup** — Windows VS Code + Claude Code stays untouched during testing period.

## Acceptance Criteria

### wsl2-claude-sandbox.AC1: Zero Permission Prompts
- **wsl2-claude-sandbox.AC1.1 Success:** Subagent runs `git status` without prompting
- **wsl2-claude-sandbox.AC1.2 Success:** Subagent runs `dotnet build` without prompting
- **wsl2-claude-sandbox.AC1.3 Success:** Subagent runs chained commands (`cd && cat`) without prompting
- **wsl2-claude-sandbox.AC1.4 Success:** Multi-task implementation plan executes without a single permission prompt

### wsl2-claude-sandbox.AC2: Windows Filesystem Isolation
- **wsl2-claude-sandbox.AC2.1 Success:** `/mnt/c/` does not exist in WSL2
- **wsl2-claude-sandbox.AC2.2 Success:** `ls /mnt/` shows no Windows drive mounts
- **wsl2-claude-sandbox.AC2.3 Failure:** Attempting to access any Windows path fails (path doesn't exist)

### wsl2-claude-sandbox.AC3: Dev Toolchain Works
- **wsl2-claude-sandbox.AC3.1 Success:** `dotnet build` succeeds for stock-analyzer and road-trip projects
- **wsl2-claude-sandbox.AC3.2 Success:** `dotnet test` passes all tests for both projects
- **wsl2-claude-sandbox.AC3.3 Success:** Python scripts in `helpers/` run correctly
- **wsl2-claude-sandbox.AC3.4 Success:** `az` CLI authenticates and runs queries

### wsl2-claude-sandbox.AC4: Database Connectivity
- **wsl2-claude-sandbox.AC4.1 Success:** EF Core migrations apply from WSL2 to Windows SQL Express via TCP
- **wsl2-claude-sandbox.AC4.2 Success:** API runs in WSL2 and reads/writes data in SQL Express
- **wsl2-claude-sandbox.AC4.3 Success:** EodhdLoader on Windows still connects via named pipes (unchanged)

### wsl2-claude-sandbox.AC5: Disposable & Rebuildable
- **wsl2-claude-sandbox.AC5.1 Success:** `wsl-setup.sh` restores full environment after `wsl --unregister`
- **wsl2-claude-sandbox.AC5.2 Success:** Rebuild takes less than 15 minutes
- **wsl2-claude-sandbox.AC5.3 Success:** After rebuild, `dotnet test` passes without manual intervention
- **wsl2-claude-sandbox.AC5.4 Success:** After rebuild, Claude Code starts with memory and plugins intact

### wsl2-claude-sandbox.AC6: State Preservation
- **wsl2-claude-sandbox.AC6.1 Success:** `~/.claude/` is a git repo backed by private `claude-config`
- **wsl2-claude-sandbox.AC6.2 Success:** Session end triggers auto-commit/push of `~/.claude/` changes
- **wsl2-claude-sandbox.AC6.3 Success:** After rebuild, memory files from previous sessions are available

### wsl2-claude-sandbox.AC7: Secrets via Key Vault
- **wsl2-claude-sandbox.AC7.1 Success:** `wsl-setup.sh` pulls all API keys from Azure Key Vault
- **wsl2-claude-sandbox.AC7.2 Success:** `.env` is generated from Key Vault values, not copied from Windows filesystem
- **wsl2-claude-sandbox.AC7.3 Success:** Adding a new key = add to Key Vault, re-run pull command
- **wsl2-claude-sandbox.AC7.4 Success:** No plaintext secrets file exists on Windows filesystem
- **wsl2-claude-sandbox.AC7.5 Success:** Key rotation = update Key Vault, re-run pull command
- **wsl2-claude-sandbox.AC7.6 Failure:** `.env` is gitignored and never committed

### wsl2-claude-sandbox.AC8: VS Code Integration
- **wsl2-claude-sandbox.AC8.1 Success:** VS Code Remote-WSL opens project in WSL2 filesystem
- **wsl2-claude-sandbox.AC8.2 Success:** Claude Code extension works through Remote-WSL
- **wsl2-claude-sandbox.AC8.3 Success:** Git operations (commit, push, pull) work from VS Code
- **wsl2-claude-sandbox.AC8.4 Success:** Windows VS Code + Claude Code (original setup) still works independently

### wsl2-claude-sandbox.AC9: Hooks Enforce Safety
- **wsl2-claude-sandbox.AC9.1 Success:** `test_hooks.py` passes all tests inside WSL2
- **wsl2-claude-sandbox.AC9.2 Success:** `git reset --hard` is blocked
- **wsl2-claude-sandbox.AC9.3 Success:** `rm -rf` is blocked
- **wsl2-claude-sandbox.AC9.4 Success:** `git push --force` is blocked
- **wsl2-claude-sandbox.AC9.5 Success:** Commits to main are blocked

## Glossary

- **WSL2 (Windows Subsystem for Linux 2)**: A compatibility layer built into Windows 11 that runs a real Linux kernel in a lightweight virtual machine. Provides a full Ubuntu environment accessible from Windows.
- **Claude Code**: Anthropic's command-line AI coding assistant. Runs as a CLI tool and VS Code extension, capable of dispatching subagents to execute shell commands autonomously.
- **Subagent**: A secondary Claude process spawned by the main session to execute a specific task (e.g., run a build, edit a file). Subagents inherit the permission configuration of the parent session.
- **`Bash(*)`**: A Claude Code permission entry that grants approval for any bash command without prompting. The `*` is a wildcard matching all commands.
- **Hooks**: Scripts wired into Claude Code's lifecycle events (pre-command, post-commit, session stop, etc.) that enforce safety rules — blocking destructive operations like `git reset --hard`, `rm -rf`, or commits to main.
- **Mirrored networking**: A WSL2 networking mode (set in `.wslconfig`) where the Linux instance shares the Windows host's network interface. Services on `localhost` are reachable from both sides.
- **`.wslconfig`**: A Windows-side configuration file (`%USERPROFILE%\.wslconfig`) that controls global WSL2 behavior, including automount and networking mode.
- **Automount**: WSL2's default behavior of mounting Windows drives (e.g., `C:\`) into the Linux filesystem under `/mnt/c/`. This document disables it to prevent Claude from accessing Windows files.
- **`wsl-setup.sh`**: The bootstrap script that installs all tooling, clones the repository, pulls secrets, and restores Claude's configuration — enabling a full environment rebuild from scratch.
- **`claude-config` repo**: A private GitHub repository storing the contents of `~/.claude/` (settings, memory files, plugin manifests). Cloned during setup so Claude's state survives distro rebuilds.
- **Azure Key Vault**: Microsoft's cloud secret management service. Used here as the authoritative store for API keys, replacing the Windows-side `.env` file as the source of truth.
- **`DesignTimeDbContextFactory`**: An EF Core interface that provides a database context at design time (e.g., when running `dotnet ef migrations`). Updated here to read a TCP-format connection string.
- **EodhdLoader**: A WPF desktop application that loads financial data from the EODHD API. Windows-only, stays on Windows, unchanged by this work.
- **WPF (Windows Presentation Foundation)**: Microsoft's Windows-only UI framework for desktop applications. Relevant here only to explain why EodhdLoader cannot run in WSL2.
- **Named pipes**: An inter-process communication mechanism used by SQL Server for local Windows connections (`.\SQLEXPRESS`). Not accessible from WSL2.
- **Blast radius**: The scope of damage a worst-case failure can cause. Here: the worst Claude can do is corrupt the WSL2 distro, which is rebuildable.
- **Remote-WSL**: A VS Code extension that connects Windows VS Code to a WSL2 environment, presenting the Linux filesystem and terminal as if working natively.
- **`Stop` hook**: A Claude Code lifecycle hook that fires when a session ends. Used here to auto-commit and push `~/.claude/` to preserve state.

## Architecture

Claude Code runs inside a WSL2 Ubuntu instance as a fully sandboxed development environment. Windows remains untouched — no drives mounted, no filesystem access. The only connection between WSL2 and Windows is TCP networking for SQL Express.

```
+--------------------------------------------------+
| WINDOWS (untouchable by Claude)                  |
|                                                  |
|  VS Code --Remote-WSL--> WSL2 Ubuntu             |
|  EodhdLoader (WPF, stays on Windows)             |
|  SQL Express (.\SQLEXPRESS, TCP:1433)            |
|  Browser (localhost testing)                     |
|  C:\Users\patri\.secrets\ (API keys, .env)       |
+------------------+-------------------------------+
                   | TCP only (mirrored networking)
+------------------v-------------------------------+
| WSL2 Ubuntu (disposable, rebuildable)            |
|                                                  |
|  Claude Code (CLI + VS Code extension)           |
|    Bash(*) permissions -- no prompts ever        |
|    Hooks enforce safety (git, SQL, rm)            |
|  .NET 8 SDK, Python 3, Node.js, Azure CLI        |
|  Repo: ~/projects/claudeProjects/                |
|  Config: ~/.claude/ (git-backed private repo)    |
|  No /mnt/c/ mount -- Windows fully isolated      |
|  Connects to SQL Express via localhost:1433       |
+--------------------------------------------------+
```

### Key Invariants

- **No Windows mounts.** WSL2 automount disabled. `/mnt/c/` does not exist. Claude's `Bash(*)` can only affect the Linux filesystem.
- **Secrets pulled from Key Vault, not copied from Windows.** During setup, `az keyvault secret show` pulls API keys and generates `.env`. No Windows filesystem access needed. Key rotation = update Key Vault, re-run pull command.
- **Hooks still active.** Safety hooks (`.claude/hooks/`) travel with the git repo and block destructive operations even with `Bash(*)`.
- **Blast radius = WSL2 distro.** Worst case: `wsl --unregister Ubuntu` and re-run setup script.

### URL Structure

No URL changes. ASP.NET Core apps in WSL2 listen on `localhost:5000` / `localhost:5100` which are accessible from Windows browser via mirrored networking.

## Existing Patterns

This is a new infrastructure setup — no existing WSL2 patterns in the codebase.

Existing patterns that carry over unchanged:
- Git workflow (develop branch, feature branches, PRs to main)
- Hook-based safety enforcement (`.claude/hooks/`)
- Project structure (`projects/stock-analyzer/`, `projects/road-trip/`, etc.)
- EF Core migrations targeting shared StockAnalyzer database

New patterns introduced:
- `wsl-setup.sh` bootstrap script for reproducible environment
- Private `claude-config` git repo for `~/.claude/` state
- TCP-based SQL connectivity (replacing named pipes + Windows auth)
- `Bash(*)` permissions (replacing per-command wildcards)

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: WSL2 Distro Setup & Isolation

**Goal:** Ubuntu distro installed with automount disabled and mirrored networking enabled

**Components:**
- `.wslconfig` on Windows — disable automount, enable mirrored networking
- Ubuntu distro installed via `wsl --install Ubuntu`
- Verify `/mnt/c/` does not exist after config
- Verify `localhost` TCP connectivity between WSL2 and Windows

**Dependencies:** None (first phase)

**Done when:** WSL2 Ubuntu boots, has no Windows filesystem access, can reach Windows services via TCP
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Dev Toolchain Installation

**Goal:** All build tools installed inside WSL2

**Components:**
- .NET 8 SDK (via Microsoft package feed)
- Python 3.10+ (via apt or deadsnakes PPA)
- Node.js (via nvm)
- Azure CLI (via Microsoft install script)
- Git configuration (user.name, user.email, SSH key or credential helper for GitHub)
- `wsl-setup.sh` script that automates all of the above

**Dependencies:** Phase 1

**Done when:** `dotnet --version`, `python3 --version`, `node --version`, `az --version`, `git status` all succeed in WSL2
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: SQL Express TCP Connectivity

**Goal:** WSL2 can connect to Windows SQL Express over TCP

**Components:**
- Windows-side: Enable TCP/IP in SQL Server Configuration Manager, start SQL Server Browser, set port 1433
- Windows-side: Enable SQL Server authentication, create SQL login
- WSL2-side: Test connection with `sqlcmd` or `dotnet` connection string
- Update `appsettings.Development.json` to support TCP connection string via environment variable with fallback
- Update `DesignTimeDbContextFactory` to read from environment variable

**Dependencies:** Phase 1 (mirrored networking)

**Done when:** `dotnet ef database update` succeeds from WSL2, targeting the Windows SQL Express StockAnalyzer database
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Repository Clone & Build Verification

**Goal:** Repo cloned into WSL2 native filesystem, builds and tests pass

**Components:**
- Clone `claudeProjects` repo into `~/projects/claudeProjects/`
- Pull secrets from Azure Key Vault via `az keyvault secret show`, generate `.env` file
- `dotnet build` for stock-analyzer and road-trip projects
- `dotnet test` for both test projects
- `python` helper scripts verified
- Add clone + secrets pull steps to `wsl-setup.sh`

**Dependencies:** Phase 2, Phase 3

**Done when:** `dotnet test` passes for all projects, `python helpers/check_links.py --all` succeeds
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Claude Code Installation & Config Restore

**Goal:** Claude Code running in WSL2 with settings/memory/plugins restored

**Components:**
- Install Claude Code in WSL2 (`curl -fsSL https://claude.ai/install.sh | bash`)
- Create private `claude-config` repo on GitHub containing current `~/.claude/` contents (settings, memory, plugin manifests)
- Clone `claude-config` as `~/.claude/` in WSL2
- Plugin source repos as git submodules
- `claude` login to authenticate
- Set `Bash(*)` and broad permissions in `~/.claude/settings.json`
- Add `Stop` hook to auto-commit/push `~/.claude/` changes on session end
- Add Claude Code install + config restore to `wsl-setup.sh`

**Dependencies:** Phase 4

**Done when:** `claude` starts in WSL2, loads plugins, has memory from previous sessions, no permission prompts for any bash command
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: VS Code Remote-WSL Integration

**Goal:** VS Code on Windows connects to WSL2 with full Claude Code functionality

**Components:**
- VS Code Remote-WSL extension (likely already installed)
- Open project folder in WSL2: `code .` from WSL2 terminal or "Open Folder in WSL" from VS Code
- Claude Code VS Code extension works through Remote-WSL connection
- Terminal, file editing, git integration all working
- Verify Claude Code subagents run without permission prompts

**Dependencies:** Phase 5

**Done when:** VS Code shows WSL2 project, Claude Code extension works, subagent dispatched and runs without any permission prompts
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: Validation & Parallel Testing

**Goal:** Verify the full workflow works end-to-end alongside existing Windows setup

**Components:**
- Run a multi-phase implementation task in WSL2 (e.g., a small feature on a test branch) to verify subagents work without prompts
- Verify hooks still block destructive operations (run `projects/hook-test/test_hooks.py`)
- Verify EodhdLoader on Windows can still connect to SQL Express (unchanged)
- Verify both Windows and WSL2 VS Code instances can coexist (not simultaneously on same repo)
- Document any issues or adjustments needed

**Dependencies:** Phase 6

**Done when:** Full implementation cycle (code, test, commit, push) works in WSL2 without a single permission prompt. Hooks verified. Windows setup still functional.
<!-- END_PHASE_7 -->

<!-- START_PHASE_8 -->
### Phase 8: PowerShell-to-Bash Script Migration

**Goal:** Rewrite PowerShell helper scripts as bash equivalents so Claude can use them in WSL2

**Components:**
- Audit all 33 `.ps1` files in `helpers/` — categorize as: needed in WSL2, Windows-only (EodhdLoader), or already has Python equivalent
- Rewrite WSL2-needed scripts as bash (`.sh`) equivalents in `helpers/`
- Update all callers (hooks, CLAUDE.md instructions, other scripts) to reference the bash versions when running in Linux
- Update `eodhd_rebuild_guard.py` to detect WSL2 environment and adjust its message
- EodhdLoader management scripts stay as `.ps1` (Windows-only, not used from WSL2)

**Dependencies:** Phase 4 (repo cloned, tools installed)

**Done when:** All scripts Claude needs in WSL2 have working bash equivalents. Hooks reference correct script versions. `python helpers/check_links.py --all` and other critical helpers work in WSL2.
<!-- END_PHASE_8 -->

## Additional Considerations

**EodhdLoader stays on Windows.** It's a WPF app — cannot run in WSL2. EodhdLoader management (rebuild, relaunch) is done from Windows. The `eodhd_rebuild_guard.py` hook should detect the WSL2 environment and adjust its message to "commit and push changes — rebuild EodhdLoader on Windows manually."

**Session state sync.** The `Stop` hook that auto-pushes `~/.claude/` ensures memory and settings survive across sessions. If Claude crashes mid-session without triggering the hook, state since last push is lost — acceptable since memory is supplementary, not critical.

**Secrets rotation.** When a key is rotated in Azure Key Vault, run a single command in WSL2 to regenerate `.env`. No Windows filesystem access needed. New keys follow the same flow: add to Key Vault, re-run pull.
