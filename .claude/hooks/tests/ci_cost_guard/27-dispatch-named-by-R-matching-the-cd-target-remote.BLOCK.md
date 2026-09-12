# `-R` naming the repo the command already `cd`s into -> still BLOCK.
#
# CH-237.10, defect 1, the composition case. The cd'd repo's origin matches
# the -R name, so resolution must land on the repo the command is actually
# about -- not refuse it as unresolvable, and not silently judge the session
# repo instead. Pins that -R parsing did not break the CH-237.9 cd path
# (fixture 21). Green before the fix by accident: the cd alone already
# blocked. It stays green after, for the right reason.
setup() {
  mkdir -p ios && ( cd ios && git init -q \
    && git config user.email t@example.com && git config user.name t \
    && git remote add origin https://github.com/acme/road-trip.git )
  mkdir -p ios/.github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' \
    > ios/.github/workflows/ios.yml
}
COMMAND="cd ios && gh workflow run -R acme/road-trip ios.yml"
ENV_VARS=(CI_RUN_OK=1)
