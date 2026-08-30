# A workflow that is not valid YAML -> BLOCK.
#
# The parse fails, so nothing can be known about the triggers. "No push trigger
# found, therefore safe" is how a gate becomes a bypass -- the same shape as a
# missing linter exiting 0. Unknowable must mean refused.
setup() {
  mkdir -p .github/workflows
  printf 'on: [push\n  jobs: : :\n    runs-on: macos-14\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
