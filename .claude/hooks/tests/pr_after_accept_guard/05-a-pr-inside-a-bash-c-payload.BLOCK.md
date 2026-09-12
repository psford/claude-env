# A `gh pr create` inside a `bash -c` payload -> BLOCK.
#
# Real bash runs the payload, so the PR really opens. The raw-text match this
# guard shipped with saw the words; CE-2.20's first token parser saw `bash`
# and stopped, which is strictly worse than what it replaced.
setup() {
  export XDG_DATA_HOME="$PWD/.xdg"
  ticket init --prefix ZZ > /dev/null 2>&1
  ticket new --type epic --title "an epic" > /dev/null 2>&1
}
COMMAND='bash -c "gh pr create --base main --head develop --title \"feat(ZZ-1): the epic\""'
