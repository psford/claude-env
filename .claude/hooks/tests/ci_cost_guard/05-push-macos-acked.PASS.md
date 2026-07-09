# `git push` in a macOS-runner repo WITH CI_MACOS_PUSH_OK=1 -> PASS.
setup() {
  mkdir -p .github/workflows
  printf 'on: push\njobs:\n  build:\n    runs-on: macos-14\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
ENV_VARS=(CI_MACOS_PUSH_OK=1)
