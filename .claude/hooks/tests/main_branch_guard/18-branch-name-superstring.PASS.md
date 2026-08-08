# 'mainline' contains 'main' but is a different branch. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND='git push origin mainline'
