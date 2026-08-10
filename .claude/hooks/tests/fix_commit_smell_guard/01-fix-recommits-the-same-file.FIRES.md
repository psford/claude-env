# A fix: commit touching a code file the PREVIOUS commit also touched. That
# overlap is the smell: the first attempt was not tested before it shipped.
setup() {
  printf 'def f():\n    return 1\n' > app.py
  git add -A && git commit -qm "feat: add f"
  printf 'def f():\n    return 2\n' > app.py
  git add -A && git commit -qm "fix: f returned the wrong value"
}
COMMAND='git commit -m "fix: f returned the wrong value"'
EXPECT_MATCH='app\.py|tested'
