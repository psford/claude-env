# `-R` naming a repo no checkout on this machine matches -> BLOCK.
#
# CH-237.10, defect 1, the refusal half. A repo this guard cannot open is a
# repo whose runners it cannot read, so it refuses rather than approves what
# it cannot inspect. The session repo HAS linux-only workflows and CI_RUN_OK=1
# is set, so the only honest rc=0 left would be "resolved the named repo and
# it is clean" -- which is exactly what cannot be established.
setup() {
  git remote add origin https://github.com/acme/session-repo.git
  mkdir -p .github/workflows
  printf 'on: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n' > .github/workflows/ci.yml
  git add -A && git commit -qm wf
}
COMMAND="gh workflow run -R acme/other-app build.yml"
ENV_VARS=(CI_RUN_OK=1)
