# Tracked file modified with a large diff, then `git restore .` (worktree form) -> BLOCK.
setup() {
  seq 1 200 > README.md
}
COMMAND="git restore ."
