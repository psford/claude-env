# CE-2.31. A dry-run git clean and an -f flag on a later command -> PASS.
#
# The git clean check walks words the same way the rm check did, so an -f
# belonging to the next statement completed `git clean -f`. The same
# statement scoping applies: a flag belongs to the command it follows.
setup() { git checkout -q -b feature/x; }
COMMAND='git clean -n && make -f Makefile'
