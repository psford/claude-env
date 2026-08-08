# refs/heads/main resolves to the same branch. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git push origin develop:refs/heads/main'
