# an unstamped file in a nested folder -> BLOCK.
#
# Every file under the card folder, at any depth.
setup() {
  put ditherware 3-looks/photos/deep/x.jpg 'photo'
}
EXPECT_MATCH='3-looks/photos/deep/x.jpg'
