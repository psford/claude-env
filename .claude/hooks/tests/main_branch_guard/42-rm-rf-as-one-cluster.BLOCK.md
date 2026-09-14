# CE-2.31. `rm -rf build`, the common spelling -> BLOCK.
#
# 38 and 39 pin the separate and long forms. The cluster itself had no
# fixture, so a change to how the rm is found could lose the one spelling
# everyone types without a test noticing.
setup() { git checkout -q -b feature/x; }
COMMAND='rm -rf build'
EXPECT_MATCH="rm -rf is forbidden"
