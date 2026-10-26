# cd to a variable then cp -> BLOCK.
#
# Where the command ends up isn't known until the shell runs, so a copy after it can't be
# judged: refused.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
}
COMMAND='cd "$D" && cp other.bin DITHERWARE.BIN'
