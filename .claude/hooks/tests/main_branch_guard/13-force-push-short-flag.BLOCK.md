# -f is force. The previous whole-string regex only matched --force. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git push -f origin feature/x'
