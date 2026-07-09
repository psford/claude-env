# `git restore --staged` only touches the index, not the worktree -> not a toss, PASS.
setup() {
  seq 1 200 > README.md
  git add README.md
}
COMMAND="git restore --staged README.md"
