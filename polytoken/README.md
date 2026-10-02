# Polytoken layer

One dev environment, two machines: this layer makes the Linux VM and the
MacBook feel like the same [polytoken](https://docs.polytoken.dev) setup —
same config, same skills/subagents, same hooks, and above all the same todo
list. GitHub is the only sync backbone: config/skills/hooks travel by git
(this repo), secrets stay per-machine on disk, and the shared todo list
lives in this repo's Issues.

```
claude-env git ──► config template, skills, subagents, hook scripts   (both machines)
GitHub Issues ──► the shared todo store (label: todo)                 (both machines)
secrets/      ──► per-machine files, referenced by $(cat …)           (never in git)
```

## Layout

| Path | What it is |
|------|------------|
| `config.template.yaml` | User-global polytoken config, byte-identical on every machine. Installed as `<config>/config.yaml`. |
| `VERSION` | The polytoken release this layer is tested against (bootstrap warns on mismatch). |
| `bootstrap.sh` | Idempotent installer: `--check`, `--rollback`, `--no-prompt`. |
| `hooks.json` | Installed as a **symlink** into `<config>/hooks.json` — hook updates arrive with `git pull`. |
| `hooks/todo-sync.sh` | `post_tool_use` (matcher `todo_*`): mirrors todo changes to Issues. |
| `hooks/todo-restore.sh` | `session_start`: injects the open tracked todos into every new session. |
| `skills/`, `subagents/` | User-global definitions, discovered via `daemon.discovery.extra_*_dirs`. |
| `secrets.example/` | One `<name>.example` per secret, instructions only. |
| `tests/` | Unit tests (fake `gh`), `run.sh` (canonical gate), `acceptance.sh` (real `gh`). |

## Bring-up — MacBook (first time)

> **Do not run the repo's top-level `bootstrap.sh`** — that one is the
> WSL2/Claude-Code setup and is wrong for the Mac. The polytoken layer's
> installer is `polytoken/bootstrap.sh` (below), and nothing else.

**The one-command path (use this):**

```sh
cd ~/projects/claude-env && git pull && bash polytoken/mac-setup.sh
```

`mac-setup.sh` repairs/creates the `~/.zshrc` entries (backed up first),
points `POLYTOKEN_CONFIG_PATH` at the git-tracked config template, symlinks
`hooks.json` into the candidate config dirs, runs `doctor`, and **posts its
report to the tracker issue** (`psford/claude-env#155`) — so the other
machine sees the result with nothing relayed by hand. It is idempotent;
re-run it after any pull that changes the layer.

1. `brew install gh jq` (plus polytoken itself per
   [docs.polytoken.dev/installation](https://docs.polytoken.dev/installation/))
2. `ssh-keygen -t ed25519` and add `~/.ssh/id_ed25519.pub` to your GitHub
   account (Patrick, manual, github.com/settings/keys)
3. `gh auth login` — Patrick's own `psford` account (it has write on
   claude-env). **The `PatricksRobot` token never goes to the Mac** — each
   machine uses its own identity.
4. `git clone git@github.com:psford/claude-env.git ~/projects/claude-env`
   — the clone path matters: `hooks.json` and the config template point at
   `~/projects/claude-env/polytoken` via `$HOME`.
5. `bash ~/projects/claude-env/polytoken/bootstrap.sh` — prompts for the
   three secrets (zai, deepseek, tavily); writes them to
   `~/.config/polytoken/secrets/` with 0600.
6. `bash ~/projects/claude-env/polytoken/tests/acceptance.sh` — must pass.
7. Start a polytoken session. The first system-reminder lists the same open
   todos as the VM. That is the two-machine moment.

## Bring-up — Linux VM

Same steps 4–6 (`gh`/`jq`/`polytoken` already installed; secrets were
seeded from the pre-layer config at install time — see
`docs/decisions.md`, polytoken layer entry). To verify an install at any
time:

```sh
bash ~/projects/claude-env/polytoken/bootstrap.sh --check    # drift report, no writes
bash ~/projects/claude-env/polytoken/tests/run.sh           # unit + shellcheck + secrets scan
```

## How the todo bridge works

Every session starts with the open `todo`-labeled issues injected into
context; every `todo_*` tool call is mirrored out-of-band (fire-and-forget,
failures only ever append to `~/.local/share/polytoken/todo-sync.log`):

- **`todo_create`** → creates a `todo`-labeled issue, unless an open issue
  with the same title exists (dedupe — adopting a tracked todo creates no
  duplicate). Issue bodies carry `session:`/`machine:`/`date:` markers.
- **`todo_complete`** → closes the matching issue (adopted items too —
  completion is the real outcome).
- **`todo_update`** → renames the issue; `in-progress` label is
  added/removed additively (an issue keeps `todo` for life, so a
  half-applied transition can never make it invisible to the restore
  query).
- **`todo_delete`** → closes the issue **only if** the deleting session is
  the one that created it (same session id AND same machine, per the body
  markers). Deleting an adopted item is session tidying and leaves the
  issue open for the next session/machine.
- **`todo_list`** → never touches GitHub, never logs (it fires constantly).

Session identity on polytoken 0.8.17: hook handlers receive no
`POLYTOKEN_*` environment variables (documented but not implemented — see
decisions entry), so `todo-restore.sh` records the current session id from
its event payload at every `session_start`, and `todo-sync.sh` reads it.
Without a session id, deletes never close (fail-safe).

Sync scripts are written for macOS's bash 3.2 (no `flock`, no GNU
`timeout`/`stat`): the sync lock is a `mkdir` lockdir with a stale-age
reclaim, and the restore timeout is a background-fetch + watchdog-kill.

## Troubleshooting

- **Session start is slow (~+5s)**: GitHub is unreachable; the restore
  served its last-good cache (`~/.local/share/polytoken/todo-restore.cache`;
  skips and sync failures land in `~/.local/share/polytoken/todo-sync.log`).
  Bare `{"outcome":"allow"}` with no list = no cache yet, still fine.
- **An issue didn't appear/close**: read
  `~/.local/share/polytoken/todo-sync.log` — every skip and failure is one
  line with the reason (dedupe skips, attribution mismatch, lock busy, gh
  failures).
- **Tracked todos missing from session start**: the injection caps at 30
  issues (`(+N more …)`); a capped backlog is a signal to finish work.
- **Config changed upstream**: `git pull`, re-run `bootstrap.sh` (backs up
  the old config first), restart the session. `--rollback` restores the
  newest backups.
- **Version warning**: the layer pins the polytoken release it was tested
  against in `VERSION`; a mismatch warns loudly but does not block.

## Deferred / known asymmetries

- **Per-machine GitHub identity (the separation-of-duties model):** the VM's
  `gh` active account is **PatricksRobot** — robot sessions author PRs,
  comment, and drive the todo bridge as the robot; Patrick approves and
  merges `main` PRs as `psford` on the web, and the robot can approve
  Patrick's PRs to satisfy the main review gate. The Mac's active account
  stays **psford** — the robot token never goes there. Switch back with
  `gh auth switch --hostname github.com --user <account>` if ever needed.
- **Saved-session goals stay machine-local** (V1). Goals-as-issues is the
  natural V2.
- **NAS deploy pipeline stays Linux-side** — Apple Silicon → x86_64 NAS
  images need buildx plumbing that is deliberately out of scope. When the
  Mac needs deploys, add a second `authorized_keys` line for it on the NAS
  `agent_deploy` user (each box its own key).
- No win32 builds on the Mac; no iOS work on Linux.

## Status

- **Linux VM: installed and verified** (unit + acceptance + live
  model/search smoke test).
- **MacBook: installed and verified (2026-10-02)** — acceptance 21/21,
  doctor green with no env overrides, and a live session answered the
  tracked-todo question from the session-start injection (AC.8, #155).
  Bring-up postmortem is in `docs/decisions.md`; `mac-setup.sh` is the
  one-command repair/verify path and posts its report to the tracker.

Day-to-day on either machine: a fresh session gets the open tracked todos
injected as context (not the sidebar — ask `what tracked todos do I
have?`, or tell it to adopt them to fill the sidebar); `todo_create`
dedupes against the tracker; `todo_complete` closes the issue;
`todo_delete` of an adopted item only tidies the session.
