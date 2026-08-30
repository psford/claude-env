# CE-5.6 — do the git-flow fragments stay parameterised?

A decision story. Most of it is not testable, and the plan should not pretend
otherwise: the deliverable is a recorded argument in `docs/decisions.md`.

## Establish the facts before arguing

- Enumerate every value the three variables actually take across all repos.
  The claim in the description is three (develop/main, trunk=master,
  trunk=main). Verify it by reading every `.claude/claude-md.json` rather than
  trusting it. If it is four or eight, the argument changes.
- Diff `git-flow-develop-main` against `git-flow-trunk` with branch names
  normalised. If they differ only in those names, enumeration means duplicating
  real prose; if they differ structurally, they were never one fragment
  wearing two values.

That second check is the one that decides it, and it has not been done.

## If the decision is to enumerate

- Every fragment links; `CLAUDE.md` becomes header plus `CLAUDE.local.md`.
  Assert no repo's CLAUDE.md contains fragment prose.
- The substitution path is deleted, not left dormant. Assert `VAR_TOKEN` and
  the exit-2 branch are gone, and that the suite's tests for them are removed
  rather than skipped.
- New risk to cover: three near-identical fragments can disagree. Assert the
  shared prose is byte-identical across them, or the duplication is the drift
  this epic exists to kill.

## If the decision is to keep the parameter

- Assert the exit-2 guard still fires when a repo's config omits a variable the
  fragment uses. That test exists; confirm it still fails on a mutation.
- The story closes on the recorded decision. That is a valid outcome.
