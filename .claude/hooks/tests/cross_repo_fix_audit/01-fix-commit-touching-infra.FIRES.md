# A fix: touching a .bicep file is the case: the same defect probably exists in
# the companion repos, and this is the reminder to go look.
setup() {
  mkdir -p infrastructure/azure
  printf 'param x string\n' > infrastructure/azure/main.bicep
  git add -A && git commit -qm "fix: the role assignment was wrong"
}
COMMAND='git commit -m "fix: the role assignment was wrong"'
EXPECT_MATCH='bicep|repo|audit'
