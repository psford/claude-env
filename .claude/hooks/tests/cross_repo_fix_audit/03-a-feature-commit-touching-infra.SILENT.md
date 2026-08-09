# New infrastructure is not a fix to audit elsewhere. Only fix: commits qualify.
setup() {
  mkdir -p infrastructure/azure
  printf 'param x string\n' > infrastructure/azure/main.bicep
  git add -A && git commit -qm "feat: add the storage account"
}
COMMAND='git commit -m "feat: add the storage account"'
