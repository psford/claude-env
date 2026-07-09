# Same large-loss scenario as 01, but an inline `# PARK-OK:` comment bypasses the guard.
setup() {
  seq 1 200 > bigfile.txt
}
COMMAND="git clean -fd  # PARK-OK: throwaway scratch data, not needed"
