# `gh workflow run` in a repo with macOS runners -> BLOCK, even with every ack env set (permanent iOS ban).
setup() {
  mkdir -p .github/workflows
  printf 'on: push\njobs:\n  build:\n    runs-on: macos-14\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="gh workflow run ios.yml"
ENV_VARS=(CI_RUN_OK=1 CI_MACOS_PUSH_OK=1)
