# a quoted heredoc marker hiding a copy -> BLOCK.
#
# "<<X" inside quotes is an argument, not a heredoc: the lines after it are commands, and an
# unstamped copy among them is refused.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
}
COMMAND=$'echo "<<X"\ncp firmware/c100/c/build/other.bin out/flash/2-x/DITHERWARE.BIN'
