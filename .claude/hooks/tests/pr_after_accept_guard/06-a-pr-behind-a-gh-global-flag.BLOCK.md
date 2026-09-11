# `gh -R owner/repo pr create` naming an unaccepted ticket -> BLOCK.
#
# gh's global flags precede the subcommand, so a fixed-slot check on argv[1:3]
# is walked past by the flag most likely to be there on a multi-repo box.
# Positional scanning is shared with ci_cost_guard now rather than written
# once per guard, which is how the two came to disagree in the first place.
setup() {
  export XDG_DATA_HOME="$PWD/.xdg"
  ticket init --prefix ZZ > /dev/null 2>&1
  ticket new --type epic --title "an epic" > /dev/null 2>&1
}
COMMAND='gh -R psford/claude-env pr create --base main --head develop --title "feat(ZZ-1): the epic"'
