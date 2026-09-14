# CE-2.31. `rm build -rf`, flags after the operand -> BLOCK.
#
# GNU rm accepts options after operands. The flag search must keep reading
# past the first operand within rm's own statement.
setup() { git checkout -q -b feature/x; }
COMMAND='rm build -rf'
EXPECT_MATCH="rm -rf is forbidden"
