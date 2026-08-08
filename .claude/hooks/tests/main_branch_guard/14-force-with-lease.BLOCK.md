# --force-with-lease is safer but still rewrites remote history. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git push --force-with-lease origin feature/x'
