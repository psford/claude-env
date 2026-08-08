# Force-pushing is forbidden on every branch, not just main. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git push --force origin feature/x'
