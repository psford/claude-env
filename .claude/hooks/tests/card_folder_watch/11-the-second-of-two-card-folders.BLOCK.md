# the second of two card folders -> BLOCK.
#
# Every project's card folder is watched, each against its own stamps.
setup() {
  put ditherware 2-x/DITHERWARE.BIN 'probe'
  stamp ditherware ditherware/out/flash/2-x/DITHERWARE.BIN
  put zz-camera 1-y/DITHERWARE.BIN 'unchecked'
}
EXPECT_MATCH='zz-camera/out/flash'
