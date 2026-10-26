# a stamp file that is not json -> BLOCK.
#
# A damaged stamp file proves nothing: fail closed.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
  printf 'not json' > firmware/c100/c/build/emulator-passed.json
}
COMMAND='cp firmware/c100/c/build/probe.bin out/flash/2-x/DITHERWARE.BIN'
