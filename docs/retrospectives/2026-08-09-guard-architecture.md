# Retrospective: the guard architecture

**2026-08-09.** Written because Patrick said it: *"the story of the past few days
has been, 'lol, that thing I built for you to stop bad things from happening
doesn't really do shit.' It's been at every layer of the stack."*

He is right, and the number that settles it is not any of the ones we have been
quoting.

## The number

    75   hook files in .claude/hooks
    48   are written so they can refuse something (exit 2 / decision: block)
     7   of those actually execute
     4   of those 7 have a fixture

**The enforcement layer is seven files.** Not seventy-five. Everything else is
either advisory, wired to an interpreter that does not exist, or wired nowhere.

The seven, and their honest state:

| guard | tested |
|---|---|
| `main_branch_guard` | yes |
| `ci_cost_guard` | yes |
| `park_before_toss_guard` | yes |
| `spec_staleness_guard` | yes |
| `absolute_path_link_guard` | **no** |
| `cap_task_timeout` | **no** |
| `merged_pr_guard` | **no** |

61% of the directory has never run once.

## It is one failure, repeated

27 fix/test commits across three days, two repos. They look like a scatter of
unrelated bugs. They are not. Sorted by root cause:

**Wrong repo, wrong context — 6.** The guard decided about a repository other
than the one in front of it. Session cwd instead of the target; the workspace
instead of the repo; data files resolved from the hook's own location; relative
paths that fail from any subdirectory.

**Prose read as a command — 6.** Heredoc bodies, commit messages and fixture
text parsed as instructions. A retrospective saying "never run git commit on
main" read as a commit. A document quoting `--force` blocking its own commit.

**Never actually in force — 3.** 44 hooks wired to `python` on a machine that
has only `python3`, failing open on every invocation for weeks. A plugin
enabled but not installed. Paths that resolve only from the repo root.

**Test asserted rather than observed — 4.** 104 green fixtures while the guard
blocked the first commit in every new repo, because no fixture could build an
unborn branch. A "runnable command" test that checked for the substring
`ticket`. A skills suite validating every flag of a command that did not exist.

**Gate logic wrong or bypassable — 5.** The bookkeeping exemption that could
launder a code change. A substring match that a semicolon disabled. A criterion
that could only be verified before the artifact that verifies it existed.

Every one of those is the same sentence: **something asserted a property that
was never observed.** The guard asserted it blocked; nobody watched it block.
The suite asserted coverage; the harness could not produce the failing input.
The dashboard asserted a gate; nothing enforced it. The activation asserted 13
hooks were live, from the one directory where the defect is invisible.

## What held, and why

This matters more than the failures, because it is not random which things
survived contact.

- **Two-party merge.** GitHub refuses to let an author approve their own PR.
  Server-side, not our code.
- **`ac remove`'s status gate.** Refused the agent deleting a criterion
  mid-implementation — a real save, on the exact scenario it was built for.
- **The state-based git hooks.** Stopped 6 of 8 commit-on-main forms, where the
  text guard stopped 2.
- **The dirty-tree handoff gate.** Fired correctly, on its author.

Not one of them parses a command string. Every one is either enforced by a
system we do not control, or reads **state** — a branch, a status field, a
staged path — rather than trying to understand an instruction.

And every failure in the taxonomy above is either a text guard inspecting
`tool_input.command`, or a test that asserts instead of observes.

The architecture has not been failing randomly. It has been **systematically
choosing the cheap mechanism.** Text guards are quick to write and nearly
worthless: they must parse bash without parsing bash, and lose to a variable, a
quote, or a heredoc. Structural controls are irritating to build and they hold.

## The four proposals

These are decisions, not conclusions. Each can be taken or refused
independently.

### 1. A control is not in force until it has been observed refusing something

Not written. Not wired. Not green. **Observed.** Every defect this week lived in
the gap between those words.

Operationally: a guard may not be counted as protection until a fixture shows it
firing on the input it exists for, and a human has seen it fire once for real.

*Cost:* slower to add guards. *Benefit:* the count of guards stops being a
number that means nothing.

### 2. Prefer the most structural mechanism available

A ladder, most binding first:

1. **Server-side** — branch protection, required reviews. Cannot be edited by
   anything in the session.
2. **State-based git hook** — handed the fact (the branch, the staged set)
   rather than parsing a string.
3. **CLI gate** — a check inside the tool that mutates the state.
4. **PreToolUse text guard** — advisory only. **Never the sole control for
   anything that matters.**

A text guard is acceptable as a fast, friendly nudge. It is not acceptable as
the thing standing between you and a bad outcome, and this week produced eleven
proofs of that.

### 3. Every wired guard has a FIRES fixture, or it gets unwired

CH-47 built the mechanism: `FIRES` / `SILENT` expectations, judged on what the
hook *said*, because an advisory hook always exits 0 and PASS/BLOCK cannot tell
a working one from a dead one.

Applied as a **precondition to wiring**, not retroactively.

### 4. Delete the inert majority

46 hooks have never executed. They are not a safety net; they are the appearance
of one, and the appearance is what let this go unnoticed for months.

Three groups:

- **~11 app-specific** — JS coordinate truthiness, C# constants, EF migrations,
  browser compat. They guard `wwwroot/js/*.js` and `.cs` files, in a repo that
  has neither. They belong to road-trip and stock-analyzer or nowhere.
- **~2 duplicate planned work** — `retro_trigger_guard` (cf. CH-24),
  `regression_test_red_verify`. Wire these rather than delete.
- **the rest** — decide per hook, on purpose rather than by neglect.

## The uncomfortable part

The deep review (CH-36) that started this was a **reading** exercise. It found
the shape of the problem and got the count wrong twice. Every specific defect in
the taxonomy above was found by *running* something, and most were found by
accident while trying to do unrelated work — two guards fired on the text of the
fixtures being written to test them; the relative-path defect surfaced because a
`cd` bricked the session.

That is the strongest argument for proposal 1. We do not find these by looking
at them.
