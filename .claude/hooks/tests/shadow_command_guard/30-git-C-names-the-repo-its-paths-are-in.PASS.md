# A git -C statement's own path operands live inside its -C directory -> PASS.
#
# CE-2.76. `git -C <harness> restore dashboard/tests/test_board.py`, run from a
# claude-env session, restores a file that already exists in the harness. The
# guard resolved the operand against the SESSION's directory instead of the -C
# directory, found no dashboard/tests there, and refused it as a new test
# root. That left the harness main checkout stuck mid-merge (2026-09-25).
#
# CWD=session puts the session in a directory with no tests root, and `other`
# holds the tracked test file, so the two bases give opposite answers: at HEAD
# this fixture is refused.
setup() {
  mkdir -p session other/dashboard/tests
  printf 'import unittest\n' > other/dashboard/tests/test_board.py
  git add -A && git commit -qm "chore: a repo whose suite already exists"
}
CWD="session"
TOOL_NAME="Bash"
COMMAND='git -C ../other restore dashboard/tests/test_board.py'
