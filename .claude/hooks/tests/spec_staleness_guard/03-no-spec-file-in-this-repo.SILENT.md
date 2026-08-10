# A repo that keeps no spec gets no opinion about its staleness.
setup() {
  git update-ref refs/remotes/origin/main HEAD
  git checkout -q -b feature/changes
  printf 'x\n' > src.py
  git add -A && git commit -qm "feat: something"
}
COMMAND='git push origin feature/changes'
