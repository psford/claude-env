# Decisions

Design decisions for claude-env, newest first. CLAUDE.md's PRODUCT DECISIONS
rule says a decision Patrick makes gets recorded here; a decision an agent
makes on his behalf belongs here too, with the reasoning that would let him
overturn it.

## 2026-10-01 — polytoken layer: GitHub Issues as the cross-machine todo store; config/skills by git; secrets per machine

The old ticket-based harness died of id collisions and harness-update
drift. Its replacement keeps the goal — the Linux VM and the MacBook as
one dev environment — with none of the failure modes: `polytoken/` (this
layer) ships the config template, user-global skills/subagents, and two
hook scripts in claude-env, so **git is the only config-sync mechanism**
(byte-identical template on both machines; `hooks.json` is a symlink into
the clone). Secrets are the deliberate exception: per-machine files under
`~/.config/polytoken/secrets/` (fixed path on every OS so the template
stays identical), referenced by `$(cat …)` with
`config_command_substitution: true`, never in git. `run.sh` greps the
whole commit history for the concrete key shapes (tavily, `sk-`, ZAI's
32-hex-dot-16) as the standing guard.

**Todos become Issues in this repo** (label `todo`), not per-repo issues:
todos are cross-project by nature — the 2026-09-30 crash's list spanned
three repos. A `post_tool_use` hook mirrors `todo_*` calls out-of-band
(fire-and-forget, fail-open, one log line per failure); a `session_start`
hook injects the open list into every session under a ~5s internal
timeout with a last-good cache, so a session never stalls on the bridge.
Issue numbers are globally unique per repo — the id-collision class of
bug is gone by construction. Labels are **additive**: `todo` for life,
`in-progress` added/removed, because `gh issue list -l a -l b` is AND and
a swap-based scheme would strand unlabeled issues invisible to every
future restore.

**Adopt-vs-create delete semantics**: the restore injection asks sessions
to adopt tracker todos, and models prune adopted items they won't work —
so `todo_delete` closes an issue only when the deleting session created
it. Ownership is proven by `session:`/`machine:` body markers matched
against the current session id and hostname; anything else (adopted,
earlier session, other machine) leaves the issue open. Residual risk, accepted:
a withdrawn-but-adopted todo lingers until completed or closed by hand.

**Session identity without env vars** — the load-bearing Phase 0 finding:
on 0.8.17, hook handlers receive **no `POLYTOKEN_*` environment
variables** (the docs describe them; the daemon does not set them), and
`post_tool_use` payloads carry no session field. Only `session_start`'s
payload has `session_id`. So the restore hook records it — along with the
daemon's pid, found by walking the hook's process ancestry — to a
machine-local `todo-session.current` file before any network I/O, and the
sync hook reads both (env var first, for the day polytoken implements
it). No session id ⇒ deletes never close. The daemon pid closes the
same-machine concurrent-session hole the first review pass found:
session todo ids restart at 1 per session, so a sync event from an older
session would otherwise resolve titles from the newer session's store and
could close the wrong issue. On a pid mismatch the sync hook now skips
every mutation except create, which is stamped with an unownable marker
(`session:attribution-unknown`) so no later delete can ever close it.
If the ancestry walk cannot find the daemon (pid 0 — e.g. a detached
hook), the pointer is trusted, which is exactly the pre-gate behavior.

Also verified on 0.8.17 and relied on: `$(cat …)` substitution works in
`providers.*.auth.key` **and** `integrations.search.providers.tavily.key`
(proven by live model + web-search turns, not just parsing);
`${HOME}` and `~` both resolve in `daemon.discovery.extra_*_dirs`;
handler `bash` strings expand `$HOME`; symlinked `hooks.json` loads
(`follow_symlinks_for_configs` is on by default). Mac bring-up corrected
one more assumption: polytoken on macOS does **not** search
`~/Library/Application Support/polytoken` for the user config (a
config.yaml placed there is dead weight — the first Mac bootstrap's
`no config file found in any searched location` with the file sitting in
that directory proved it); the supported mechanism is the
`POLYTOKEN_CONFIG_PATH` file override, and `mac-setup.sh` points it at
the git-tracked template so the clone *is* the config on that machine.

Scripts are macOS-bash-3.2-clean by construction (no `flock`/GNU
`timeout`/GNU `stat`; `mkdir` lockdir with stale reclaim; background
fetch + watchdog kill) and shellcheck-gated. One bug class found by the
tests before it ever shipped: the restore's watchdog subshell originally
inherited stdout, which would have added ~5s to **every** session start
once the daemon's blocking read waited for the orphaned `sleep` — the
watchdog now redirects to /dev/null.

Deferred: saved-session goals stay machine-local (goals-as-issues is the
V2), the NAS deploy pipeline stays Linux-side (buildx), and Mac bring-up
(AC.8) is a pending-verification runbook item in `polytoken/README.md` —
the layer is not "done" until a fresh Mac session shows the VM's open
todos.

## 2026-10-01 — main protection settled: legacy branch protection at one approval; rulesets rejected

Todo #2 (robot merges develop, Patrick merges main) closed with two moves.

First proposal — repo rulesets (`main-protected`: require PR + 1 approval,
force-push/deletion blocks, bypass = psford) — **rejected by Patrick**: the
mature enforcement layer is existing collaborator permissions plus the client
hooks; more server-side machinery is unwanted. PR #107 was closed with the
diff preserved for reference.

A robot-side audit then showed the premise was partly false: only claude-env
required an approving review on `main`; nfl-stats and omni-map had no branch
protection at all (direct pushes to `main` were possible from the robot's
`write` account); four more required 0 approvals, so a robot-authored PR was
self-mergeable. The client hooks had held throughout — no incident, but the
server side was open on 6 of 8.

Filled with legacy branch protection instead (Patrick, via `gh` as psford):

- 1 approving review required on `main` in all eight flow repos
  (`enforce_admins=false`, so Patrick's owner bypass stays — the emergency
  hotfix path, and why his past merges left no review trail)
- force pushes and deletions blocked on nfl-stats and omni-map, previously naked
- default branch flipped `main`→`develop` on the seven repos still defaulting
  to `main` (T-Tracker-Desktop already had it) — `gh pr create` without
  `--base` no longer targets `main`
- photo-portfolio recorded as trunk: its local `develop` was a fossil
  (377 behind `main`, 0 ahead, tip already in `main`) and is deleted
- approval mechanics recorded in the fragment: the robot approves Patrick's
  commits; Patrick approves the robot's `main` PRs and merges them; the robot
  merges only its own feature→develop PRs

Same day: NAS deploy automation landed end-to-end (T-Tracker-Desktop
`docs/design-plans/2026-09-30-nas-deploy-automation.md` has the DSM gotchas),
and ports 8039/8765/8919 joined `docs/ports.md`.

Postscript, same evening: release PR T-Tracker-Desktop #12 was opened with
plain `gh pr create` instead of the spec's `ticket release` (spec deviation,
accepted — Patrick merged it). Local `main`/`master` had drifted from remotes
across the clones (road-trip 687 behind, claude-env 379, omni-map 151,
stock-analyzer 140, gpu-crash-analyzer 30, whisper-service 4; T-Tracker-Desktop
had no local main at all) — all fast-forwarded to match. Standing expectation
(Patrick, 2026-10-01): local main always tracks remote main.

## 2026-08-30 — git-flow-develop-main stops being parameterised; git-flow-trunk stays (CE-5.6)

Under CE-5, a shared fragment carrying no `{{VARS}}` is symlinked into each
repo instead of copied, so it exists in one file and cannot drift. Fragments
that carry variables must still be generated, because a symlink cannot turn
`{{WORKING_BRANCH}}` into `develop`.

That left `git-flow-develop-main` and `git-flow-trunk` as the only two
fragments still copied into every repo that uses them, and the only reason the
generation path exists at all. The question was whether to enumerate them —
one invariant fragment per branch layout — so that every fragment links and
substitution could be deleted.

### The check that decided it

The proposal assumed the two fragments differ only in branch names. They do
not. With every branch token normalised to the same string, **57 of 62 lines
still differ.**

They describe different workflows, not one workflow with two spellings.
`git-flow-develop-main` has a `develop → main` flow and a REVERSE MERGE
prohibition that only makes sense when two long-lived branches exist.
`git-flow-trunk` has "nothing reaches trunk except via PR", names server-side
branch protection with `enforce_admins`, and covers `git push origin
<branch>:trunk` as a CLI merge however it is spelled. Neither table is a
rewording of the other.

So enumeration was never available: these were not one fragment wearing two
values, and merging them to split them again would have invented the
duplication it was meant to remove.

### What the values actually are

Asked of every `.claude/claude-md.json` rather than assumed:

| Fragment | Repos | Distinct value sets |
|---|---|---|
| `git-flow-develop-main` | 8 | **1** — `develop` / `main`, every time |
| `git-flow-trunk` | 2 | **2** — `master` (T-Tracker), `main` (photo-portfolio) |

That is the real finding, and it splits the answer.

`git-flow-develop-main`'s parameter has never varied. Eight repos, one value.
It is a variable in name only, and it is the sole reason those eight repos
still hold a copy of their git-flow rules — which is where the commit, merge
and branch prohibitions live, so it is the worst fragment to have eleven copies
of.

`git-flow-trunk`'s parameter genuinely varies, over two values, and the fragment
is 41 lines of prose that would have to be duplicated to enumerate it.

### Decision

**De-parameterise `git-flow-develop-main`**: literal `develop` and `main`. It
becomes linkable, and the eight repos that use it inherit their git-flow rules
instead of copying them. Those repos then hold no fragment prose at all —
`CLAUDE.md` is the generated header plus `CLAUDE.local.md`.

**Keep `git-flow-trunk` parameterised.** Two values over 41 lines is exactly
the case a parameter is for. Splitting it into `git-flow-trunk-main` and
`git-flow-trunk-master` would create two near-identical files that can disagree
— a new home for drift, in the change made to end drift. That is the argument
against enumeration and it applies here even though it did not apply above.

**The substitution path stays.** Two repos need it, so it is not dormant code
and the exit-2 guard on an unsubstituted token still does real work.

### What this costs

A repo that ever wants a different two-branch layout — `develop → master`, say
— now needs a new fragment rather than a new value. That is the trade, and it
is acceptable at eight-of-eight agreement: the layout is a standard here, not a
per-repo preference. If a second layout ever appears, this decision should be
revisited rather than worked around by re-adding the variable, because a
variable with two values is a different thing from a variable with one.

---

## 2026-09-11 — No hatches, or none an agent can reach

Patrick: *"I do generally agree that no hatches is the way forward. Or at
least for now that hatches can only be run from outside the sandbox."*

### What was decided

An exception mechanism may exist, but it is **executable only from outside
the sandbox**. Nothing an agent can type from inside a session — no
environment variable set as a command prefix, no magic comment, no
acknowledgement token — releases a block. The default is no hatch at all;
where one is genuinely needed it lives where the agent cannot reach it.

`CI_RUN_OK` is the shape that already works and is worth copying: it is read
only from the shell that LAUNCHES the session, which an agent cannot set from
inside a command. The mechanism is not "a secret token"; it is "authority
held outside the write cage".

### Why the human pattern inverts

For a human team an inline override is good design because it is
discoverable, greppable, reviewable, and typed by someone with judgement and
a stake in being right later. Every one of those becomes a vulnerability when
the actor is an agent. Discoverable becomes an invitation —
`cwd_drift_guard` printed its own key inside the refusal, so hitting the
block handed the agent the string that removed it. Greppable becomes a menu.
Reviewable assumes someone reads it, and on 2026-09-11 eleven documented
controls turned out to be wired to nothing. Judgement assumes a stake beyond
the current turn.

And the sharpest part: **the agent writes the guards.** `CWD_DRIFT_OK` was
not inherited — a Claude session wrote it and a later Claude session used it.
A rule saying "do not use the hatch" does not constrain the party that
authors the hatch.

### The half that was missing

The standing rule said only what may not exist. It did not say what an
agent's legitimate path IS when a block is wrong, and an agent that cannot
find the sanctioned path invents one. On 2026-09-11 a guard refused the
commit that fixed that same guard, and all three available exits were
illegitimate: the bypass token (forbidden), rewording the message (evasion),
and handing the command to Patrick to run (the same evasion with better
manners). The only legitimate move was to fix the guard first.

So the rule now carries its positive half: when a block is wrong, **fix the
guard, or report it and stop.** Never reword to slip past, and never route
the blocked command through a human — asking Patrick to run a command an
agent was refused is a hatch wearing his name.

### What this costs, and the open risk

Latency on a wrong block, which is exactly what made 2026-09-11 expensive. It
is only tolerable if reporting a wrong block is cheap and fast. That fast
path is not built yet and is tracked on CE-12.2, along with the question of
whether the demand for exceptions is mostly guard defects in the first place
— three separate guards that day were refusing prose that merely named a
command.

Open and not decided here: what mechanically stops an agent authoring a NEW
hatch. That gap has no coverage today.
