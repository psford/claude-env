# The ordinary case this guard must never obstruct. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND='git push origin develop'
