# A push aimed elsewhere with `git -C` -> judged against THAT repo -> BLOCK.
#
# CH-237.9, AC1, the other half of 21. `-C` moves one invocation without moving
# the shell, so a guard reading the session's cwd sees a repo with no workflows
# and approves a push that starts a macOS job in the repo next door.
setup() {
  mkdir -p ios && ( cd ios && git init -q \
    && git config user.email t@example.com && git config user.name t )
  mkdir -p ios/.github/workflows
  printf 'on:\n  push:\njobs:\n  build:\n    runs-on: macos-15\n' \
    > ios/.github/workflows/ios.yml
}
COMMAND="git -C ios push origin main"
