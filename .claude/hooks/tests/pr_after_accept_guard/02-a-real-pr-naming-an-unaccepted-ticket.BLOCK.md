# A real `gh pr create` whose title names a ticket that is NOT accepted -> BLOCK.
#
# This is the case the hook exists for, and it must survive the parser change:
# narrowing what counts as "creating a PR" must not narrow it past the act.
setup() {
  export XDG_DATA_HOME="$PWD/.xdg"
  ticket init --prefix ZZ > /dev/null 2>&1
  ticket new --type epic --title "an epic" > /dev/null 2>&1
}
COMMAND='gh pr create --base main --head develop --title "feat(ZZ-1): the epic"'
