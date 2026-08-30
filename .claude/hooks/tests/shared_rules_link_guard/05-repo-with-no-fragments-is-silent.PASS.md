# A repo that consumes no shared fragments has no claude-md.json -> PASS.
# Most directories on this machine are in this category, and a repo that never
# opted in must not be opted in by a guard.
setup() {
  printf 'changed\n' > app.py && git add app.py
}
COMMAND="git commit -m 'work'"
