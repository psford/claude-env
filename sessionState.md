# Session State

_Last updated: 2026-08-30_

## Where things stand

| Repo | State |
|------|-------|
| claude-env | `develop` @ `bfb3ea0`, pushed, 5 ahead of `main`, no PR |
| claude-harness | `develop` @ `63f3ae8`, pushed, no PR |
| omni-map | `feature/OM-2-coverage` @ `2815c44`, pushed, **24 ahead of `main`, no PR** |
| stock-analyzer | `fix/bicep-appservice-sku-p0v3` @ `1dfaf49`, pushed, no PR |
| road-trip | `develop` @ merge of `origin/develop`, **UNPUSHED — blocked, see CE-2.8** |
| SysTTS / whisper-service / gpu-crash-analyzer | `develop`, pushed |
| T-Tracker | PR #21 merged to `master` |
| photo-portfolio | PR #57 merged to `main`; deploy is still manual `cf:deploy` and was NOT needed |
| win-audio-analyzer | off the shared layer on Patrick's call, committed on `chore/sync-claude-md`, unpushed (Windows-side) |

## What happened

**CE-5 is accepted.** Eleven copies of the shared rules became one file.

A fragment carrying no `{{VARS}}` is byte-identical in every repo, so it is
symlinked at `.claude/rules/<name>.md` instead of pasted into `CLAUDE.md`. All
ten linked repos resolve to one inode — not ten files that agree, one file.
`git-flow-develop-main` joined them in CE-5.6; `git-flow-trunk` stays generated
because its two consumers genuinely disagree (`master` vs `main`).

The failure mode changed and got **quieter**: drift was two files disagreeing,
absence is a repo that inherits nothing while looking healthy. `--check` refuses
three shapes (not a symlink, dangling, misdirected) and `shared_rules_link_guard`
now runs it on every commit — wired once in `~/.claude/settings.json`, because
wiring eleven repos is the problem the epic exists to kill.

**CH-192.1** lets a commit name a ticket from another repo's board when it is
`in_progress` there. Built mid-epic because the cross-repo wall blocked the
rollout twice; omni-map alone had cost Patrick three button presses.

## The pattern worth carrying forward

Three defects came from **controls that could not fail** — a mutation that
changes nothing is usually saying the test never tested that:

- `--check` was not read-only. It called `makedirs` before its own guard, so it
  built the directory the mutation was looking for.
- The new guard could be bypassed by ANY env prefix: `VAR=1 git commit` was not
  recognised as a commit at all, so the escape-hatch fixture had been passing
  whether or not the hatch worked.
- `git -C $var` makes every guard judge the session's repo instead of the target
  (CH-192.2) — an unexpanded shell variable resolves to nothing and falls back
  silently.

Also: CE-5.6's own premise was false, and the test plan caught it. It assumed
the two git-flow fragments differ only in branch names; with tokens normalised,
57 of 62 lines differ. Checking before arguing is what produced the real answer.

## Open, needing Patrick

- **road-trip cannot be pushed.** `ci_cost_guard` refuses and tells you to use
  `CI_MACOS_PUSH_OK=1 git push`, which cannot work — it reads `os.environ` and a
  hook runs in Claude Code's process. Filed as **CE-2.8**, with a second defect:
  its refusal claims a push can trigger macOS work, but road-trip's only macOS
  workflow is `workflow_dispatch`-only. Do not soften the macOS policy.
- **omni-map has 24 commits and no PR** to `main`.
- **CH-224.18**: a finished epic never reaches Patrick's queue, so it can never
  be closed. CE-5 and OM-1 were the first two to hit it and had to be closed by
  pasted command.

## Also filed, not started

`CH-224.16` mechanical-check cannot read bash test names (claude-env's suites are
bash, so every CE criterion resolves N/C and gets hand-checked).
`CH-224.17` no registry of local ports — 8787 collided and cost a day of pushes.
`CH-192.2` the shell-variable path bug above.
`CE-2.8` as described.
