# `on: [workflow_dispatch]` -- a non-push trigger in the SEQUENCE form -> PASS.
#
# The fixture that tells reading from failing-to-read. 11 and 12 use the scalar
# and sequence forms with `push`, so they block either way: found the trigger,
# or could not parse it and refused. Both are rc 2 and neither notices when the
# str/list handling is deleted -- a control proved exactly that.
#
# Here the answer differs. Read correctly, this is dispatch-only and passes.
# Read by a mapping-only reader, the triggers come back unknown and it blocks.
setup() {
  mkdir -p .github/workflows
  printf 'on: [workflow_dispatch]\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
