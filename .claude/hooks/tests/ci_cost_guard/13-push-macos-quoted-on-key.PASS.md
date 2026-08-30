# `"on":` quoted, dispatch only -> PASS.
#
# YAML 1.1 reads a bare `on:` key as the BOOLEAN True, so a workflow's triggers
# live under the key True and d["on"] raises KeyError on a perfectly valid file.
# Quoting the key changes which of those two happens. Both spellings must reach
# the same verdict, or the guard's answer depends on how somebody typed a key
# rather than on what the workflow does.
setup() {
  mkdir -p .github/workflows
  printf '"on":\n  workflow_dispatch:\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
