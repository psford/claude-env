# a baseline entry for another folder -> BLOCK.
#
# A baseline entry covers its own card folder only: the same name and bytes in another
# project's folder are not accepted by it.
setup() {
  put ditherware 2-x/DITHERWARE.BIN 'same'
  accept ditherware 2-x/DITHERWARE.BIN
  put zz-camera 2-x/DITHERWARE.BIN 'same'
}
EXPECT_MATCH='zz-camera/out/flash'
