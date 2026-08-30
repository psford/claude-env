# CE-5.4 — photo-portfolio and T-Tracker

Two repos with blockers. The plan's job is to keep an honest report from being
turned into a partial success.

## photo-portfolio

`defer_forever_guard` refuses any CLAUDE.md commit there. That refusal is
correct and is not to be bypassed, and `DEFER-PERMANENT` is a marker Patrick
writes, not one this story writes on his behalf.

- Run the conversion, attempt the commit, and record the refusal verbatim with
  its real exit code. A failing run is evidence.
- The refusal must be parsed only far enough to name the file, the offending
  lines and the missing fields. Do not summarise it into "blocked".
- Confirm the guard is what blocks: with the deferred lines temporarily given
  an Owner and Due **in a scratch copy outside the repo**, the same commit
  succeeds. That distinguishes this guard from any other reason the commit
  might fail, and it never touches Patrick's content.

## T-Tracker

Trunk-based, no develop branch.

- Assert `git branch --show-current` before doing anything, and assert the
  commit does not land on trunk. The failing input is a script that assumes
  `develop` exists and commits to whatever is checked out.
- The PR must be created and its URL recorded. An unpushed branch is not a
  delivered conversion.
- `git-flow-trunk` carries `{{TRUNK_BRANCH}}` and stays generated, so this repo
  is one link plus one generated fragment — the same mixed case as CE-5.2, on a
  different fragment.

## The assertion that matters most

The story's evidence must list, by name, every repo still holding copies when
it closes. A rollout that reports "done" while two repos are unconverted is the
failure this epic exists to remove, reproduced one level up.
