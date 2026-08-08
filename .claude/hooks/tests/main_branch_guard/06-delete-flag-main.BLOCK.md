# Explicit --delete of the production branch. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git push origin --delete main'
