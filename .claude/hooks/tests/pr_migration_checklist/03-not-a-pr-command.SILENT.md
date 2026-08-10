# Reading PRs is not creating one.
setup() {
  mkdir -p Migrations
  printf 'public partial class Init { }\n' > Migrations/20260809120000_Init.cs
  git add -A && git commit -qm "feat: add the migration"
}
COMMAND='gh pr list --state open'
