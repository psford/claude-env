# Session State

_Last updated: 2026-08-23_

## Where things stand

| Repo | State |
|------|-------|
| claude-harness | `develop`, 3 commits ahead of main: `3ffd4bc`, `024602d`, `da03d2c`. Clean. Dashboard still serving `60a4cf3` — the new commits are NOT deployed. |
| T-Tracker_win | branch `fix/tt7-routes-query` @ `29a7850`, not merged, no PR. Working tree shows ~30 files as modified: these are 644→755 mode flips from the /mnt/c mount, NOT changes. Use `git -c core.fileMode=false status`. |
| claude-env | `develop`, only this file + claudeLog.md. No code changes. |

## The night's unfinished business (read this first)

Two QA agents were dispatched as Patrick went to bed and their verdicts had
not landed when this was written: **CH-179** (claude-harness, internal — ends
at QA per CH-161, does NOT reach Patrick's queue) and **TT-7** (T-Tracker_win,
`requires_uat`, so QA's accept sends it to Patrick). Check both with
`ticket show` before assuming anything about their state.

## Waiting on Patrick

- **CH-166 token vocabulary** — the one open design decision. `host_requires`
  is an open list of free-form tokens; nothing defines the legal set, so a
  typo makes a ticket no machine can ever claim. Recommendation on the table:
  derive the legal vocabulary from declared `host.json` files (the hosts ARE
  the registry) rather than maintaining a separate list. Must be settled
  before CH-172 ships — retrofitting the filing path afterwards is worse.
- **CH-167** (Windows build runner) — filed, still `draft`, awaiting scope
  approval.
- **TT-7 AC4** — unverifiable until the NAS collector is restarted on
  `29a7850`. Nudge him; do not do it.
- **Sandbox SB-1/2/9** are still on his board in `~/projects/harness-sandbox`.
  Clear with `bash sandbox/reset.sh --remove` when he is done clicking.

## What happened today

Started as "check on T-Tracker", became the first real end-to-end exercise of
the harness against non-harness work. It found a lot.

**Shipped.** TT-7: `/api/routes` took 13–16s against the NAS because
`GetLoggedRoutes` was the one dedup caller with no WHERE, so its ROW_NUMBER
window scanned and sorted the whole observation table. Rewritten as an
aggregate over a new covering index: 1.82s → 0.26s on a copy of the real
1.09M-row database, identical counts.

**CH-179 landed** (gate 4 exemption + filing/ready validation for
`--test-plan`), and with it the settled contract: the analyst writes the plan,
commits it, and only then moves the story to `ready`.

## Patrick's standing criticism — the live thread

He called the harness "baroque, rube-goldberg-ass" after the first real use
produced stranded files, and he is right on the evidence:

- **181 tickets in claude-harness against 8 in T-Tracker_win** — ~22:1 of
  process about process.
- **Eight escape hatches** in the ticket CLI (`--allow-dirty`,
  `--allow-unscoped`, `--mid-review-ok`, `--parallel-ok`, `TICKET_ORPHAN_OK`,
  `TICKET_PARALLEL_OK`, `TICKET_WATCH_TMP_OK`). Three were used in one honest
  session. Every hatch marks a rule that was wrong and got a bypass instead of
  a correction.
- Both defects found today had the SAME shape: **two individually-correct
  rules with a hole between them.** Rules grow linearly, interactions
  quadratically, tests linearly — so holes appear faster than they are found.
- His own rule says gate hard on deployed apps and NOT on local toolchest.
  claude-harness is toolchest and is the most heavily gated thing he owns.

**He is not being a pedant** — he said so explicitly, and he is right:
"Defining and enforcing process is the only way I can really see to make this
all work." The gates repeatedly caught real things today, and two analysts hit
gate 4 and REPORTED it rather than faking an `in_progress` claim. That is the
system working.

The distinction that came out of it, and the one to apply going forward:
**a rule the correct actor cannot satisfy is not enforcement, it is a
deadlock.** Gate 4 did not stop a bad commit; it stopped a good one and pushed
the work outside git. Keep every gate that blocks something bad; fix or delete
the ones that only block the right person doing the right thing.

## Epics filed today (all from real defects, not speculation)

| ID | What | State |
|----|------|-------|
| CH-165 | Board starts one way, roots in durable config | approved → CH-169/170/171 |
| CH-166 | A story says which machine can finish it | approved → CH-172–176 |
| CH-167 | Windows build runner, started manually | draft, awaiting scope |
| CH-177 | The harness does not quietly swallow what it was given | approved → CH-178/179/180 |
| CH-181 | Retire the watcher's wake mechanism | approved → CH-182/183/184 |

## The watcher, and the thing that replaced it

The watcher notified nobody for an entire session; when finally run by hand it
dumped 13 missed tickets. Not a bug — a subprocess cannot wake a Claude
session, so the design made EXITING the notification: a snare that catches once
and must be re-armed. Patrick: "are we hunting? is it a snare? it's dumb."
CH-153 filed this exact diagnosis on 2026-08-21, ended "needs a decision", and
was CANCELLED without the decision being made.

**The answer was a primitive already in the harness: `Monitor`** with
`persistent: true`. It streams stdout into the session as notifications for the
session's life. Proven end to end — Patrick clicked Reject in the browser, the
board recorded it, and the event arrived in ~5s with no polling and no ping.

```
Monitor(persistent=true, command=
  'cd ~/projects/claude-harness && while true; do python3 \
   plugins/psford-tickets/bin/ticket-watch.py $ROOTS 5 \
   --only-actor human || true; sleep 1; done')
```

`$ROOTS` is the two configured roots, spelled out:

    /home/patrick/projects
    /mnt/c/Users/patri/Documents/claudeProjects/projects  # STALE-PATH-OK: WSL carve-out, not the old monorepo root

**ARM THIS AT SESSION START.** Nothing prompts anyone to, which is exactly why
a whole session ran blind. CH-183 puts it in the session protocol properly; the
`while true` wrapper is a workaround that CH-182's `--loop` flag deletes.

## Windows development — what the session established

- **WSL cannot execute Windows binaries at all.** No `WSLInterop` entry in
  `/proc/sys/fs/binfmt_misc`. Not a permissions question; `dotnet.exe` and
  `powershell.exe` are unreachable with or without approval.
- **`dotnet build ./TTracker.sln` fails in WSL** (MSB4019 — WindowsDesktop SDK
  absent). One `net8.0-windows` project poisons the whole-solution build, so
  the repo's full gate structurally cannot run here. Build projects
  individually: Core, Data, Service are all `net8.0` and work.
- `networkingMode=mirrored` in `.wslconfig`, so **localhost crosses both ways**
  — verified, Windows ports 135/445 answer from WSL. A Windows-side runner on
  127.0.0.1 is reachable. Windows has .NET SDKs 8.0.418, 8.0.424, 9.0.315.
- **Runner safety, Patrick's decision:** manual start IS the control, no
  autostart. His reasoning, which is correct: the trust boundary is already
  crossed every time he pastes a command into PowerShell; what changes is who
  initiates and how often a human is in the loop. Allowlisted verbs are kept
  for accident-prevention and legibility, NOT as security — `dotnet build`
  runs MSBuild targets, which execute arbitrary code, so an allowlist bounds
  which repo's build runs, not what code runs.
- **The board and the watcher were both blind to T-Tracker_win** because
  `--root` only named `~/projects`. CH-170 must fix this for BOTH readers, not
  just the server.

## Standing agreements (carried forward)

- Two-surface rule: dashboard is Patrick's; CLI refusals must print what
  happened, why, and the exact way forward (memory: feedback_two_surface_rule).
- One story in flight; while anything is in_review/uat the only work is its
  review (memory: feedback_one_story_in_flight).
- The dashboard IS production: deploys only via deploy-dashboard.sh's smoke
  gate; restart = deploy (memory: feedback_dashboard_is_production).
- Gates are built only for failures that already cost real work.
- UAT ticks are affirmative: unchecked by default, Accept demands them.
- QA works for Patrick, not for the dev — never QA your own code.
