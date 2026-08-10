# Only fix: commits are judged. Every commit re-touching a file is normal work.
setup() {
  printf 'def f():\n    return 1\n' > app.py
  git add -A && git commit -qm "feat: add f"
  printf 'def f():\n    return 2\n' > app.py
  git add -A && git commit -qm "feat: f now returns two"
}
COMMAND='git commit -m "feat: f now returns two"'
