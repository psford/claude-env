# `if gh workflow run x; then ...` -> the hard deny still fires.
#
# A keyword takes a COMMAND as its operand, so the verb sits one token further
# right than the argv scan looks. `if`, `while`, `until`, `time` and `!` all do
# this, and all of them were denied by the raw string match that CE-2.20
# replaced.
#
# `statements()` splits on `;`, so this arrives as `if gh workflow run x` with
# argv0 `if` -- a command by itself, and not one that dispatches anything.
COMMAND="if gh workflow run ios-ci.yml; then echo done; fi"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
