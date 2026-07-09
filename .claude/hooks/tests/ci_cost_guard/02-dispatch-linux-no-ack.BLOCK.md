# `gh workflow run` in a Linux-runner repo without CI_RUN_OK -> BLOCK.
setup() {
  mkdir -p .github/workflows
  printf 'on: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n' > .github/workflows/ci.yml
  git add -A && git commit -qm wf
}
COMMAND="gh workflow run ci.yml"
