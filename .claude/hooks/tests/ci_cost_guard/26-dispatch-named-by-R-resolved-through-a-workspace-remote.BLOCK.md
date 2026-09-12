# `gh workflow run -R owner/repo` naming an iOS repo -> judged against THAT repo -> BLOCK.
#
# CH-237.10, defect 1. Nothing parsed -R/--repo: the guard read the workflows
# of whatever directory the SESSION started in, found none, and did not even
# ask for CI_RUN_OK. This is the realistic path -- any session told to kick the
# iOS workflow in the repo next door.
#
# Resolution walks the workspace repos' origin remotes (the sibling layout
# under ~/projects in production; CLAUDE_WORKSPACE_ROOTS points the same
# machinery at the scratch workspace here).
#
# CI_RUN_OK=1 is set deliberately: it lifts the metered-linux block and must
# NOT lift this one.
setup() {
  mkdir -p ios && ( cd ios && git init -q \
    && git config user.email t@example.com && git config user.name t \
    && git remote add origin https://github.com/acme/road-trip.git )
  mkdir -p ios/.github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' \
    > ios/.github/workflows/ios.yml
}
COMMAND="gh workflow run -R acme/road-trip ios.yml"
ENV_VARS=(CI_RUN_OK=1 CLAUDE_WORKSPACE_ROOTS="$repo")
