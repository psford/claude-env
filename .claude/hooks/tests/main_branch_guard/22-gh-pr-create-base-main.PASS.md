# Opening a PR against main is the sanctioned path, not a bypass. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND='gh pr create --base main --head develop'
