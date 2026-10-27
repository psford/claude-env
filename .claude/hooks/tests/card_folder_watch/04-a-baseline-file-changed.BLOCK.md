# a baseline file changed -> BLOCK.
#
# The baseline accepts bytes, not names: the same file with new bytes is a new file.
setup() {
  put ditherware 5-fullres/DITHERWARE.BIN 'accepted'
  accept ditherware 5-fullres/DITHERWARE.BIN
  put ditherware 5-fullres/DITHERWARE.BIN 'changed since'
}
EXPECT_MATCH='5-fullres/DITHERWARE.BIN'
