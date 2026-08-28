# Session State

_Last updated: 2026-08-27_

## Where things stand

| Repo | State |
|------|-------|
| claude-harness | `develop` @ `92251d8`, clean, 6 commits ahead of `main`, no PR open. Dashboard serving `6806787` — behind. |
| claude-env | `develop` @ `801dd7f`, 1 commit ahead of `main`. This file is the only change. |

## What happened this session

Read `claude-harness/docs/design/004-handoff-2026-08-27.md` and continued from
it. Armed the board watch first, which immediately paid for itself: Patrick moved
CH-222 draft → ready while the handoff was still being read, and the event
arrived in the session.

**CH-222.1 is accepted** — housekeeping files (`sessionState.md`, `claudeLog.md`,
`.claude/settings*.json`) are now bookkeeping for gate 4. That is what removes
the reason CE-1 was invented.

The implementation is not the three strings it looks like. `BOOKKEEPING_PREFIXES`
is matched with `startswith` and every existing entry is a directory. Two of the
new entries are exact root filenames and one is a glob, so the guard grew a
second and third matching rule: an exact-name tuple, and an anchored regex whose
wildcard is explicitly `[^/]*`. `fnmatch` is the trap to avoid — its `*` matches
`/`, so `.claude/settings*.json` would have matched `.claude/settings/hooks/`.

## Two defects found by process rather than by reading

**Mutation found a test passing for the wrong reason.** `stage()` accumulates
across `subTest` iterations and `only_tickets_are_dirty()` restores only
`src/app.py`, so a path staged in iteration 1 was still dirty in iteration 2 and
was what blocked the commit. A guard matching the log names with `endswith`
survived a test written specifically to kill it. Fixed with a `clean_tree()`
helper, applied to every looping test including the pre-existing
`test_a_lookalike_directory_gets_no_exemption`, which had the same shape.

**QA found silent evidence loss.** `ticket ac verify --by` is `action="append"`,
so the clauses of a multi-part criterion must arrive in ONE invocation. Running
the command again for the same AC replaces what was there, printing a
confirmation each time. Ten successful-looking commands left five links, and the
discarded five were the ones that matched the criteria. `mechanical-check` passed
on the survivors — it asks whether a reference resolves, not whether it resolves
to the mechanism the AC names.

Filed as **CH-223** (draft epic, needs Patrick's scope call) with **CH-223.1**
under it. The fix is deliberately not chosen: whether re-verifying an AC is ever
meant to be a correction decides between "refuse the second call" and "make the
loss visible". First job under the epic is checking whether `set`, `qa` and `uat`
share the shape.

## Open, and what it needs

- **CH-223** — draft. Needs Patrick's scope approval before anything moves.
- **CH-222.2** — `--ongoing` epics, depends on CH-222.1 which is now accepted, so
  it is unblocked. Still draft.
- **CH-222.3** — a note held for the future UI pass, not work.
- **CH-215 / CH-216** — the feedback follow-up flag. Decided, still draft.
- **CH-167, CH-192** — ready epics, untouched this session.

## Environment notes worth keeping

- **Patrick's global git ignore** (`~/.config/git/ignore`) carries
  `**/.claude/settings.local.json`. That path never reaches `git status` on this
  machine, so any test staging it passes or fails depending on whose config runs
  it. CH-222.1's test uses `.claude/settings.ci.json` instead.
- **`test_install.py` is not machine-isolated.** `install.sh` scopes the `ticket`
  symlink to `TICKET_BIN_DIR`, which the test overrides, but computes
  `watcher_dst` from `XDG_DATA_HOME`, which it does not — so the watcher-install
  step always touches the real machine path. It passes here and fails in a
  worktree. Pre-existing, untouched by CH-222.1, not yet filed.
- **Six stale agent worktrees** under `claude-harness/.claude/worktrees/`, four
  pinned to old commits, plus a prunable `/tmp` entry. Two QA agents in a row ran
  the wrong code because of them — the first noticed only because the test count
  was 48 instead of 53. `git worktree prune` is the cleanup, not yet run.

## Standing agreements (carried forward)

- Questions to Patrick go on the board via `ticket ask`, then STOP. He does not
  read the transcript for questions.
- Only say "waiting on you" when a control exists on his surface.
- Two-surface rule: dashboard is Patrick's; CLI refusals print what happened, why,
  and the exact way forward.
- One story in flight; while anything is in_review the only work is its review.
- The dashboard IS production; restart = deploy, via `deploy-dashboard.sh`.
- QA works for Patrick, not the dev — never QA your own code.
- Mutation testing is standing approval. Mutate both directions and expect a
  split; a mutant set that kills everything proves nothing.
