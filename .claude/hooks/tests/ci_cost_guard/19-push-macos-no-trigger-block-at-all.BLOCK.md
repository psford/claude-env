# A workflow with a macOS job and NO `on:` key -> BLOCK.
#
# The file parses cleanly, so the malformed-YAML path never runs; the triggers
# are simply unknowable. A control proved this was unasserted: treating an
# unreadable trigger set as safe passed the whole suite, because 14 blocks via
# the parse exception rather than through this branch.
#
# Unknown must mean refused. GitHub would reject a workflow with no triggers,
# so this shape should not exist -- which is the point. A guard that decides a
# file it does not understand is harmless is not a guard.
setup() {
  mkdir -p .github/workflows
  printf 'name: orphan\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
