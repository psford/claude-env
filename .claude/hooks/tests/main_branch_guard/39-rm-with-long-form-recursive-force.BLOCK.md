# CE-2.29. `rm --recursive --force` in long form -> BLOCK.
#
# The same act as `rm -rf`, and the pattern before CE-2.29 let it through:
# `--recursive` carries no f after its r, and `--force` carries no r before
# its f, so neither word matched the single-cluster regex. Pinned so the
# long form cannot quietly slip back out.
setup() { git checkout -q -b feature/x; }
COMMAND='rm --recursive --force build'
EXPECT_MATCH="rm -rf is forbidden"
