# Records the dormancy contract rather than the alarm. The hook returns before
# reading anything unless an eodhd-loader directory exists — it belongs to
# stock-analyzer, and in every other repo it must be silent. That dormancy is
# the property worth pinning: it is wired globally.
setup() {
  printf 'x\n' > loader.py
  git add -A && git commit -qm "feat: loader"
}
COMMAND='git commit -m "feat: loader"'
