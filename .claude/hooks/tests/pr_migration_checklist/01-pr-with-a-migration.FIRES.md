# A PR to main carrying a new EF Core migration is what this exists for.
# The hook diffs origin/main...HEAD, so the fixture has to give it an origin/main
# to diff against — otherwise it finds nothing and the test would pass for the
# wrong reason.
setup() {
  git update-ref refs/remotes/origin/main HEAD
  mkdir -p Migrations
  printf 'public partial class Init { }\n' > Migrations/20260809120000_AddParkBoundaries.cs
  git add -A && git commit -qm "feat: add the migration"
}
COMMAND='gh pr create --base main --head develop --title "release"'
EXPECT_MATCH='migration'
