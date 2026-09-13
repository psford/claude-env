# CE-2.29. `rm -r -f` with the flags written separately -> BLOCK.
#
# The same act as `rm -rf`, and the pattern before CE-2.29 let it through: it
# only matched r-then-f inside ONE hyphenated cluster. Checked by reading
# the old regex rather than assumed, then pinned here. The flags are now
# recognised whether clustered or apart.
setup() { git checkout -q -b feature/x; }
COMMAND='rm -r -f build'
EXPECT_MATCH="rm -rf is forbidden"
