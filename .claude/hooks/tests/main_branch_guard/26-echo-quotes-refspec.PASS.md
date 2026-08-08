# Writing the string to a file is not performing it. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND="echo 'git push origin develop:main' >> notes.md"
