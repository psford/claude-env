# CE-5.2 — claude-env and claude-harness stop copying their own shared rules

Run: `bash helpers/tests/test_sync_claude_md.sh`, plus the repo checks below.

## The case that is actually new

Every earlier test built a fake claude-env and a fake repo as siblings.
claude-env is not a sibling of itself. Its link runs `.claude/rules/00-universal.md
-> ../../shared/claude-md/00-universal.md`, two levels rather than three, and
nothing has ever exercised that.

Build a workspace where the repo IS the env root and assert the computed target
has no `..` escaping the repo. The failing input is the script assuming the
omni-map shape: it would emit `../../../claude-env/...`, which from inside
claude-env points at a sibling directory named claude-env that does not exist.
That link would dangle, and `--check` would catch it — so the test must assert
the *target string*, not merely that the link resolves on this machine, where a
wrong-but-lucky path could still land.

## The mixed case

Both repos take one linkable fragment and one generated one. Assert together:
the link exists AND the branch names are substituted in CLAUDE.md AND no
`{{VAR}}` survives. Any one of those alone passes under a script that got the
split backwards.

## Not obvious

- **Second run is a no-op.** Run the script twice; the link must be identical
  and CLAUDE.md unchanged. A script that unlinks and recreates every time
  churns git status for nothing.
- **An existing regular file at the link path.** The previous state of these
  repos is a copy, so conversion must replace a real file with a link. Seed one
  and assert it is replaced, not skipped and not appended to.
- **`--check` before conversion.** It must exit 3, not 0, on a repo still
  holding copies. If it exits 0 the check cannot drive the rollout.

## Controls

Point the link at the wrong fragment inside the same repo — it resolves,
reads fine, and delivers the wrong rules. `--check` must still refuse.
