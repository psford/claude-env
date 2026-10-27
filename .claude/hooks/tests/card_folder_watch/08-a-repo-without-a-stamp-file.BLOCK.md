# a repo without a stamp file -> BLOCK.
#
# Nothing stamped, so a new file can only be refused.
setup() {
  put ditherware 2-x/DITHERWARE.BIN 'unchecked'
}
EXPECT_MATCH='2-x/DITHERWARE.BIN'
