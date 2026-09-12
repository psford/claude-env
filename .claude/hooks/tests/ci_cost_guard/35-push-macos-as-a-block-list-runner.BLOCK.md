# A macOS runner written as a block LIST under runs-on -> BLOCK on push.
#
# CH-237.10, defect 5, second shape, on the push-reachability path:
#   runs-on:\n    - macos-15
# The macos string sat on the next line, so the prefilter never matched and
# the push-reachability scan skipped the file entirely.
setup() {
  mkdir -p .github/workflows
  printf 'on: push\njobs:\n  build:\n    runs-on:\n      - macos-15\n' \
    > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
