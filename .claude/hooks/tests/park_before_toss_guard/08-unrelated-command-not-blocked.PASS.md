# A command that doesn't match any discard pattern at all -> PASS.
setup() {
  seq 1 200 > bigfile.txt
}
COMMAND="ls -la"
