# A NEW tests root inside the -C directory is still refused -> BLOCK.
#
# CE-2.76 moves where a git operand is judged, not what is judged there. A
# checkout that would call a tests root into being under `other`, where none
# exists and no runner sits above it, is the act the rule blocks, -C or not.
setup() {
  mkdir -p session other
  printf 'x\n' > other/notes.md
  git add -A && git commit -qm "chore: a repo with no tests root"
}
CWD="session"
TOOL_NAME="Bash"
COMMAND='git -C ../other checkout HEAD -- newroot/tests/test_x.py'
