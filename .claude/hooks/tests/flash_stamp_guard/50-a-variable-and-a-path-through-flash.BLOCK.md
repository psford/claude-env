# a variable and a path through flash -> BLOCK.
#
# Narrowing the match to paths must still refuse a destination built at run time beside a
# path into the card folder.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'module bytes\n' > firmware/c100/c/build/probe.bin
}
COMMAND='cp firmware/c100/c/build/probe.bin "out/flash/$N/DITHERWARE.BIN"'
