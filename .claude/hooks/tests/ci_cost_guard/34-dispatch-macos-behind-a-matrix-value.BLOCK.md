# A macOS runner that only exists as a matrix VALUE -> BLOCK.
#
# CH-237.10, defect 5. `runs-on: ${{ matrix.os }}` with `os: [macos-15,
# ubuntu-latest]` puts no `macos` on the runs-on line, so the runner was
# invisible on the dispatch path (and the push path). One matrix leg bills
# the full 10x minutes.
#
# CI_RUN_OK=1 is set deliberately: the permanent ban, not the metered block.
setup() {
  mkdir -p .github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: ${{ matrix.os }}\n    strategy:\n      matrix:\n        os: [macos-15, ubuntu-latest]\n' \
    > .github/workflows/build.yml
  git add -A && git commit -qm wf
}
COMMAND="gh workflow run build.yml"
ENV_VARS=(CI_RUN_OK=1)
