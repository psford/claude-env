# Same large-loss scenario as 01, but PARK_OK=1 env var bypasses the guard.
setup() {
  seq 1 200 > bigfile.txt
}
COMMAND="git clean -fd"
ENV_VARS=(PARK_OK=1)
