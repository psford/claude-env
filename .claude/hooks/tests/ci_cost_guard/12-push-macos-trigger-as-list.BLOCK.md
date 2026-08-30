# `on: [push, pull_request]` -- the sequence form -> BLOCK.
setup() {
  mkdir -p .github/workflows
  printf 'on: [push, pull_request]\njobs:\n  build:\n    runs-on: macos-14\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
