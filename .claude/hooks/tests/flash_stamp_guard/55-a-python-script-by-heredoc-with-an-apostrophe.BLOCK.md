# a python script by heredoc with an apostrophe -> BLOCK.
#
# The apostrophe no longer makes the command unreadable; the script still names the card
# folder, so it is refused for that.
setup() {
  mkdir -p out/flash/2-x
}
COMMAND=$'python3 - <<\'EOF\'\n# the probe\'s module\nopen("out/flash/2-x/DITHERWARE.BIN", "wb").write(b"x")\nEOF'
