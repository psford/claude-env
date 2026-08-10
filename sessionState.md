# Session State

_Last updated: 2026-08-09_

## Where things stand

| Repo | State |
|------|-------|
| claude-env | `main`, clean. PRs #51–#53 merged. 158 hook tests. |
| claude-harness | `main`, clean. PRs #26–#34 merged. 355 checks. |
| photo-portfolio | `main`, deployed. Untouched today. |

## Waiting on Patrick

- **CH-46** — `needs_input`. Is the hook table decidable, or must the never-run rows be run first?
- **CH-47** — `uat`. AC3 asked whether any of the 13 fired on something it had no business
  judging. **Two did**; both fixed with regression fixtures. False as history, true as of now —
  that difference is the verdict.

## What happened (2026-08-09)

### The enforcement layer is six guards, not seventy-five

    75  hook files
    48  written so they can refuse something
     6  of those actually execute   <- the real enforcement layer
     6  now tested (was 4 of 7)

`merged_pr_guard` (7 fixtures, stub `gh` on PATH), `absolute_path_link_guard` (5, synthetic
transcript) and `cap_task_timeout` (6 python tests) had never been watched work.
`cap_task_timeout` left the count: it rewrites `updatedInput` rather than refusing.

### One failure, repeated at every layer

27 fix commits over three days sort into five root causes that are all the same sentence:
**something asserted a property that was never observed.** Full taxonomy in
`docs/retrospectives/2026-08-09-guard-architecture.md`.

What held — two-party merge, the `ac remove` status gate, the state-based git hooks — has one
thing in common: none of it parses a command string.

### The retrospective caught its own disease

Proposal 4 ("delete the inert majority") was withdrawn mid-execution. The classifier for
"app-specific hooks safe to delete" returned 15 candidates, 2 flatly wrong — a regex over source
text, about to delete files, which is the grep-audit mistake the document criticises.

claude-env exists to host tooling that runs in **other** repos. The 46 "never executes" split
35 wired-here-on-the-dead-interpreter / 9 wired nowhere / 2 companion-only. The 35 are not
dormant, they are **lying**. Replaced by **4': wiring must not lie** — which is CH-48's job.

**Nothing was deleted.**

### Also shipped

- **CH-52** — the gate-4 bookkeeping exemption could launder a code change. Demonstrated: two
  source files landed in a commit naming no ticket. Now judges the working tree, not the index.
- **CH-50** — dashboard verdicts. Patrick's first one arrived `via: dashboard` on the story that
  built it. Epic scope approval deliberately has no button.
- **CH-51/53/55/56/58** — `ac remove` gated, the epic scope gate made real, the queue's commands
  fixed, `install.sh`, and hooks reading their own repo's data.

## Known gaps, not fixed

- **4' is outstanding.** 35 hooks still wired on an interpreter that does not exist.
- Proposals 2 and 3 are rules in a document. Nothing enforces them.
- `ac_staleness_guard` writes stderr, not `additionalContext` — it fires on every push and
  reaches nobody. Deliberately left; changing what appears on every push is its own decision.
- **CH-57** — `ac remove` is gated; cancel-and-refile achieves the same thing and is not.
