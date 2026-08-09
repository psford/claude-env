# A fix: in application code is not infrastructure and is nobody else's problem.
setup() {
  printf 'def f():\n    return 1\n' > app.py
  git add -A && git commit -qm "fix: off-by-one in f"
}
COMMAND='git commit -m "fix: off-by-one in f"'
