# `git push` in a repo with macOS-runner workflows without ack -> BLOCK.
setup() {
  mkdir -p .github/workflows
  printf 'on: push\njobs:\n  build:\n    runs-on: macos-14\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
