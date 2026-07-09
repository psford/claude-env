# `rm` targeting an untracked file carrying >=150 lines of uncommitted state -> BLOCK.
setup() {
  seq 1 200 > bigfile.txt
}
COMMAND="rm bigfile.txt"
