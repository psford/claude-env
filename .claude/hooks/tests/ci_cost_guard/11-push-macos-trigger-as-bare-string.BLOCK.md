# `on: push` -- the scalar form rather than a mapping -> BLOCK.
#
# The three trigger spellings parse to three different Python types (str, list,
# dict) and a reader that handles only one of them silently decides the others
# are not push-triggered. That failure allows a push it should refuse.
setup() {
  mkdir -p .github/workflows
  printf 'on: push\njobs:\n  build:\n    runs-on: macos-14\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
