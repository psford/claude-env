# Recorded, not celebrated: with no origin/main ref the hook finds nothing and
# says nothing, even with a migration sitting in the tree. That is its real
# behaviour in a fresh clone or a repo with a differently-named remote, and a
# fixture is how it stays a known limitation rather than a surprise.
setup() {
  mkdir -p Migrations
  printf 'public partial class Init { }\n' > Migrations/20260809120000_AddParkBoundaries.cs
  git add -A && git commit -qm "feat: add the migration"
}
COMMAND='gh pr create --base main --head develop --title "release"'
