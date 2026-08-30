# Manually dispatching a macOS workflow -> BLOCK, permanently, unchanged.
#
# CE-2.8 relaxes the PUSH path only. This is the path the 2026-07-08 incident
# came through -- three iOS builds in seven minutes, three weeks of quota gone --
# and it has no bypass by design. A fixture here so the relaxation cannot creep
# into it: the workflow is dispatch-only, which is exactly what now makes a PUSH
# pass, and dispatching it must still be refused.
setup() {
  mkdir -p .github/workflows
  printf 'on:\n  workflow_dispatch:\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="gh workflow run ios.yml"
ENV_VARS=(CI_RUN_OK=1 CI_MACOS_PUSH_OK=1)
