# `gh workflow run` in a Linux-runner repo WITH CI_RUN_OK=1 -> PASS.
setup() {
  mkdir -p .github/workflows
  printf 'on: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n' > .github/workflows/ci.yml
  git add -A && git commit -qm wf
}
COMMAND="gh workflow run ci.yml"
ENV_VARS=(CI_RUN_OK=1)
