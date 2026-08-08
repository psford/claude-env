# Empty source deletes the remote branch. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git push origin :main'
