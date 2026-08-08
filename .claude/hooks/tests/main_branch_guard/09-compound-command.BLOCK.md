# The push is the second statement of a compound command. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git add -A && git push origin develop:main'
