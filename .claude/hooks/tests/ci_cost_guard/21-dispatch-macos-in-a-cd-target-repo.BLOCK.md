# A dispatch that `cd`s into an iOS repo -> BLOCK, permanently.
#
# CH-237.9, AC1. The guard used to resolve ONE repo -- the session's cwd -- and
# ask its workflows the question. So the permanent macOS ban was chosen by
# whichever directory Claude Code happened to start in, and a dispatch reached
# road-trip untouched from any session that was not road-trip.
#
# CI_RUN_OK=1 is set here deliberately. It lifts the metered-linux block and
# must NOT lift this one: the macOS ban has no bypass by design.
setup() {
  mkdir -p ios && ( cd ios && git init -q \
    && git config user.email t@example.com && git config user.name t )
  mkdir -p ios/.github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' \
    > ios/.github/workflows/ios.yml
}
COMMAND="cd ios && gh workflow run ios.yml"
ENV_VARS=(CI_RUN_OK=1)
