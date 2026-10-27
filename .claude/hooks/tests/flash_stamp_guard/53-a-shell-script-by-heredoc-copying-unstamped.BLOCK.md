# a shell script by heredoc copying unstamped -> BLOCK.
#
# A body fed to an interpreter is a script, not data: one that names the card folder is
# refused, as fixture 26's python is.
setup() {
  mkdir -p firmware/c100/c/build out/flash/2-x
  printf 'other bytes\n' > firmware/c100/c/build/other.bin
}
COMMAND=$'bash <<\'EOF\'\ncp firmware/c100/c/build/other.bin out/flash/2-x/DITHERWARE.BIN\nEOF'
