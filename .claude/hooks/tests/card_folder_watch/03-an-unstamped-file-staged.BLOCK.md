# an unstamped file staged -> BLOCK.
#
# The case the watch exists for: a file in the card folder that no command named, so the
# PreToolUse gate never saw it, and no harness stamped.
setup() {
  put ditherware 2-x/DITHERWARE.BIN 'unchecked'
}
EXPECT_MATCH='2-x/DITHERWARE.BIN'
