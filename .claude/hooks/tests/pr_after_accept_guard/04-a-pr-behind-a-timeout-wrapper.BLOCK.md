# `timeout 900 gh pr create` naming an unaccepted ticket -> BLOCK.
#
# The same weakening the CSO found in deploy_guard, in its sibling. CE-2.20's
# first parser read argv0, so every wrapper in front of `gh` turned a refusal
# into silence -- and the whole point of this guard is that unreviewed work
# must not reach Patrick as a PR.
setup() {
  export XDG_DATA_HOME="$PWD/.xdg"
  ticket init --prefix ZZ > /dev/null 2>&1
  ticket new --type epic --title "an epic" > /dev/null 2>&1
}
COMMAND='timeout 900 gh pr create --base main --head develop --title "feat(ZZ-1): the epic"'
