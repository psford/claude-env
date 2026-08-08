# Flags before the remote must not be read as refspecs. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND='git push -u origin feature/thing'
