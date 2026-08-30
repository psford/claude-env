# The same macOS job, reachable from a push -> BLOCK.
#
# The other half of 09. One line differs: the trigger. This is the case the
# guard is actually for, and it must not weaken.
setup() {
  mkdir -p .github/workflows
  printf 'on:\n  push:\n    branches: [main]\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
