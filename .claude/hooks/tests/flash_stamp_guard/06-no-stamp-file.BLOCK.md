# no stamp file -> BLOCK.
#
# No harness has stamped anything: nothing can be staged.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
}
COMMAND='cp firmware/c100/c/build/probe.bin out/flash/2-x/DITHERWARE.BIN'
