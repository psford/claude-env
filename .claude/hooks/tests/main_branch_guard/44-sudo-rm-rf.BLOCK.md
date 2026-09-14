# CE-2.31. rm behind a wrapper -> BLOCK.
#
# The fix reads rm only as a command word, not as part of a flag. A wrapper
# in front of it must not hide it.
setup() { git checkout -q -b feature/x; }
COMMAND='sudo rm -rf build'
EXPECT_MATCH="rm -rf is forbidden"
