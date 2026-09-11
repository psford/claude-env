# A dispatch behind a plain `env` wrapper -> BLOCK.
#
# CH-237.10, defect 2, second shape. `env` (assignments optional) merely
# execs what follows it, but argv0 was env so _kind saw nothing. Same rule
# as 29: what the wrapper runs, the guard reads.
setup() {
  mkdir -p .github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="env gh workflow run ios.yml"
ENV_VARS=(CI_RUN_OK=1)
