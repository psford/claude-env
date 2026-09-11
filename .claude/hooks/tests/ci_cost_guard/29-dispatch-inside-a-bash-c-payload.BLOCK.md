# A dispatch hidden inside a `bash -c` payload -> BLOCK.
#
# CH-237.10, defect 2. argv0 is bash so _kind saw nothing, and the raw-text
# fallback only fires when NOTHING parsed -- the statement list was full of
# tokens that merely failed to look like what they were. Real bash runs the
# payload; the guard must read it.
#
# CI_RUN_OK=1 is set deliberately: this must land as the permanent macOS ban,
# not as the metered-linux block.
setup() {
  mkdir -p .github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="bash -c 'gh workflow run ios.yml'"
ENV_VARS=(CI_RUN_OK=1)
