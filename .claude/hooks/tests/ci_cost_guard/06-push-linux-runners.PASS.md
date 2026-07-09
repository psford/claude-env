# `git push` in a repo with only Linux runners -> PASS silently (zero friction).
setup() {
  mkdir -p .github/workflows
  printf 'on: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n' > .github/workflows/ci.yml
  git add -A && git commit -qm wf
}
COMMAND="git push origin main"
