# Bare push is fine when the current branch is not trunk. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND='git push'
