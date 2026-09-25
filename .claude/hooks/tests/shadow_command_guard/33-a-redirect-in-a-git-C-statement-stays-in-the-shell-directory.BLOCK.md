# A redirect in a git -C statement lands where the SHELL is -> BLOCK.
#
# CE-2.76. -C moves git, not the shell: `> tests/test_x.py` writes under the
# session's directory whatever -C names. The -C directory here HAS a tests
# root and the session does not, so a fix that wrongly carried -C over to the
# redirect would judge it inside an existing suite and allow it. It must
# still be refused: the session has no tests root, and this creates one.
setup() {
  mkdir -p session other/tests
  printf 'import unittest\n' > other/tests/test_existing.py
  git add -A && git commit -qm "chore: the -C directory has a suite; the session does not"
}
CWD="session"
TOOL_NAME="Bash"
COMMAND='git -C ../other show HEAD:notes.md > tests/test_x.py'
