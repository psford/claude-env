# a line after a heredoc copying unstamped -> BLOCK.
#
# Only the body up to its delimiter is data: the command after it is judged as any other.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
}
COMMAND=$'git commit -q -F - <<\'EOF\'\nmessage\nEOF\ncp firmware/c100/c/build/other.bin out/flash/2-x/DITHERWARE.BIN'
