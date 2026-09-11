# `gh api .../actions/runs/ID/rerun` -> dispatch class -> BLOCK.
#
# CH-237.10, defect 4. The dispatch class required the literal "dispatches"
# in a gh api call, so the rerun endpoint walked past it -- and a rerun
# re-bills a full macOS run. CI_RUN_OK=1 is set so only the permanent macOS
# ban can explain the block.
setup() {
  mkdir -p .github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="gh api -X POST repos/acme/rt/actions/runs/9876543210/rerun"
ENV_VARS=(CI_RUN_OK=1)
