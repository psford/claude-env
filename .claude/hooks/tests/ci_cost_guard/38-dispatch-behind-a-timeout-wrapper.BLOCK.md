# A dispatch behind `timeout` -> BLOCK as the permanent macOS ban.
#
# This guard's own WRAPPERS list knew sudo/env/nohup/nice/command/exec/xargs
# and never learned `timeout`, so the wrapper this box actually uses was the
# one gap. Found by the CSO gate on 2026-09-11 while judging CE-2.20.
#
# timeout's DURATION is an operand, not a flag: the walk must consume exactly
# one bare word after the options or it reads `900` as the command.
#
# CI_RUN_OK=1 is set deliberately so this lands as the permanent macOS ban
# rather than the metered-linux block.
setup() {
  mkdir -p .github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="timeout 900 gh workflow run ios.yml"
ENV_VARS=(CI_RUN_OK=1)
