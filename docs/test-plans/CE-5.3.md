# CE-5.3 — the five unblocked repos inherit by link

Repos: stock-analyzer, road-trip, SysTTS, whisper-service, gpu-crash-analyzer.

Run: `helpers/sync-claude-md.sh --check <repo>` for each, exit 0; plus the
suite, plus the per-repo assertions below.

## The case that is actually new

Two links in one repo. Every earlier test linked exactly one fragment, so
nothing has proved the loop handles a second — a script that overwrote
`.claude/rules/` per fragment instead of adding to it would pass every existing
test and leave each of these repos with one link instead of two.

stock-analyzer and road-trip take `stack-web-azure`; SysTTS and whisper-service
take `stack-windows-service`; gpu-crash-analyzer takes `stack-windows-util`.
Assert the count of links per repo, not merely that `00-universal.md` is one.

## Not obvious

- **The stack fragments are linked for the first time.** Assert each resolves
  and reads the same bytes as its source. A fragment nobody has linked before
  is where a filename assumption would surface.
- **Branch names must still differ per repo.** All five take
  `git-flow-develop-main`, so all five generate the same text — which is fine,
  and is exactly why it must be checked rather than assumed. Assert each
  CLAUDE.md names that repo's own branches and carries no `{{VAR}}`.
- **A repo whose branch is not `develop`.** Do not create branches. Read
  `git branch --show-current` per repo first and record it; three of the five
  have not been checked. A repo on trunk belongs in CE-5.4, not here.
- **CLAUDE.md shrinks.** Assert the line count drops by roughly the fragment's
  length. A conversion that adds the link but forgets to stop pasting leaves
  both, and every existence check still passes.

## Controls

Per repo: remove one of its two links and confirm `--check` exits 3 and names
that fragment. Removing the *second* link matters more than the first — a loop
that only ever validates `linked[0]` passes the obvious control.
