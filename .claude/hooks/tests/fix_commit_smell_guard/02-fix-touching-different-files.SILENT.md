# A fix: for something the previous commit never touched is not a re-fix.
setup() {
  printf 'def f():\n    return 1\n' > app.py
  git add -A && git commit -qm "feat: add f"
  printf 'def g():\n    return 2\n' > other.py
  git add -A && git commit -qm "fix: g was missing"
}
COMMAND='git commit -m "fix: g was missing"'
