# master is protected on the six repos that use it as trunk. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git push origin develop:master'
