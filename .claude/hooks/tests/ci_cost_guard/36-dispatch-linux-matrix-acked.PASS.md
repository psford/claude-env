# A linux-ONLY matrix repo, acked -> PASS.
#
# CH-237.10, companion to 34. The tightening must not become a blanket
# refusal: a matrix reference whose values resolve to linux-only is clean,
# and with CI_RUN_OK=1 the metered dispatch is acknowledged. A guard that
# cannot tell "matrix with macos" from "matrix without macos" would block
# every matrix repo forever, which costs exactly the trust CE-2.8 was filed
# over. Same role for defect 5 that 25 and 07 play for CH-237.9.
setup() {
  mkdir -p .github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: ${{ matrix.os }}\n    strategy:\n      matrix:\n        os: [ubuntu-24.04, ubuntu-latest]\n' \
    > .github/workflows/ci.yml
  git add -A && git commit -qm wf
}
COMMAND="gh workflow run ci.yml"
ENV_VARS=(CI_RUN_OK=1)
