# A quoted -m argument is one token, never an invocation. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND="git commit -m 'never run git push origin HEAD:main'"
