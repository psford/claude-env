# `on: workflow_dispatch` -- the same, in the SCALAR form -> PASS.
#
# The other half of 17. Sequence and scalar are separate branches in
# _push_triggers and a fixture that exercised only one would let the other rot.
setup() {
  mkdir -p .github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
