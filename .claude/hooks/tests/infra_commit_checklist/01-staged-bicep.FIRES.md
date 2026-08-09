# A staged .bicep file is infrastructure: the checklist is the whole point.
setup() {
  mkdir -p infra
  printf 'param location string = resourceGroup().location\n' > infra/main.bicep
  git add infra/main.bicep
}
COMMAND='git commit -m "feat: add the storage account"'
EXPECT_MATCH='bicep|infrastructure|checklist'
