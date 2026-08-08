# Naming main in a read command is not a push. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND='git log --oneline main'
