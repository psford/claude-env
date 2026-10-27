# a heredoc piped into an interpreter -> BLOCK.
#
# cat only reads the body, but the pipe hands it to python: a script that names the card
# folder, refused.
setup() {
  mkdir -p out/flash/2-x
}
COMMAND=$'cat <<\'EOF\' | python3 -\nopen("out/flash/2-x/DITHERWARE.BIN", "wb").write(b"x")\nEOF'
