# CE-2.31. `git clean -fd` -> BLOCK.
#
# No fixture refused git clean at all, so scoping its flag search could lose
# the real case silently. This pins it.
setup() { git checkout -q -b feature/x; }
COMMAND='git clean -fd'
EXPECT_MATCH="git clean -f deletes untracked files"
