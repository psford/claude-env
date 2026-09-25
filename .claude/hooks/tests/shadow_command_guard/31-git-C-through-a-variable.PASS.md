# The same restore with the -C directory held in a variable -> PASS.
#
# CE-2.76. The command actually refused was spelled `H=<repo>; git -C $H
# restore ...`. The guard expands the assignment first (CE-2.39), so this case
# turns on the same -C fix as fixture 30. It is here so the spelling that was
# refused in the field stays covered.
setup() {
  mkdir -p session other/dashboard/tests
  printf 'import unittest\n' > other/dashboard/tests/test_board.py
  git add -A && git commit -qm "chore: a repo whose suite already exists"
}
CWD="session"
TOOL_NAME="Bash"
COMMAND='O=../other; git -C $O restore dashboard/tests/test_board.py'
