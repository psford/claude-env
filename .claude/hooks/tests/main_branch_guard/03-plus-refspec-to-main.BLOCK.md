# Leading + requests a non-fast-forward update of main. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git push origin +develop:main'
