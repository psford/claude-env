# Same merge, spelled with HEAD as the source. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git push origin HEAD:main'
