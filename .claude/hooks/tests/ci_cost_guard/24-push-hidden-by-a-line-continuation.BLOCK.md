# A push split over two lines by a trailing backslash -> BLOCK.
#
# CH-237.9, AC2. Same defect as 23 on the push path, and it fails for a
# slightly different reason worth pinning separately: `_is_push` asked
# `"push" in tokens[1:]`, which is a membership test and not a positional one,
# so it survives extra flags. It does not survive the token becoming '\npush'.
#
# The raw-text regex fallback does not save it either -- that only runs when
# the statement list comes back EMPTY, and here it comes back full of tokens
# that merely fail to look like a push.
setup() {
  mkdir -p .github/workflows
  printf 'on:\n  push:\njobs:\n  build:\n    runs-on: macos-15\n' \
    > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND=$'git \\\npush origin main'
