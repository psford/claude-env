# a heredoc redirected into the card folder -> BLOCK.
#
# cat only reads its heredoc, but the redirect writes into out/flash/.
setup() {
  mkdir -p out/flash/2-x
}
COMMAND=$'cat > out/flash/2-x/notes.txt <<\'EOF\'\nanything\nEOF'
