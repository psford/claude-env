# CE-2.31. rm handed its arguments by xargs, after a pipe -> BLOCK.
#
# Scoping flags to their own statement splits at the pipe. The rm and its
# flags sit together in the second statement, so it is still refused.
setup() { git checkout -q -b feature/x; }
COMMAND='find . -name build | xargs rm -rf'
EXPECT_MATCH="rm -rf is forbidden"
