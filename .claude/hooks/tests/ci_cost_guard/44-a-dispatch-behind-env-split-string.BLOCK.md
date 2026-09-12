# The LONG spelling of `-S`. The short one was enumerated; this one was not, and coreutils runs both.
#
# CE-2.20, QA round 2. Round 0 was wrappers, round 1 was shell syntax,
# and this is round 3: indirection. Each round was a construct absent
# from a finite list of known hiding places, which is why that list was
# replaced by the opposite question -- authority is granted only to text
# that is plainly commands and separators.
#
# CI_RUN_OK=1 so this lands as the permanent macOS ban rather
# than the metered-linux block.
setup() {
  mkdir -p .github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND='env --split-string '\''gh workflow run ios.yml'\'''
ENV_VARS=(CI_RUN_OK=1)
