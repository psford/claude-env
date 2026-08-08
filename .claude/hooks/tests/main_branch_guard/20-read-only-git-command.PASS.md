# Reads are never blocked. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND='git ls-remote --heads origin'
