# The 2026-08-07 violation: a fast-forward merge to main spelled as a push. -> BLOCK.
setup() { git checkout -q -b feature/x; }
COMMAND='git push origin develop:main'
