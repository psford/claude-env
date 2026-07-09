# Large untracked file + `git clean -fd` -> BLOCK (loss estimate >= threshold).
setup() {
  seq 1 200 > bigfile.txt
}
COMMAND="git clean -fd"
