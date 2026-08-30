# A macOS job that a push CANNOT reach -> PASS.
#
# CE-2.8, and the whole point of the ticket. road-trip's ios-ci.yml is exactly
# this: macos-15, dispatch-only, because the iOS app is developed on a Mac and
# GitHub is permanently banned from building it. A push there cannot spend a
# single 10x minute, and the guard blocked every push anyway.
#
# Deliberately identical to 10-*.BLOCK.md except for the trigger. Changing the
# runner too would let this pass for the wrong reason.
setup() {
  mkdir -p .github/workflows
  printf 'on:\n  workflow_dispatch:\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
