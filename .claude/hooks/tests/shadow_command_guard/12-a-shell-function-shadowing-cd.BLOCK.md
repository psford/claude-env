# A shell function shadowing a builtin -> BLOCK.
#
# The guard's docstring claimed this family from the start -- "a bash function
# named `kill` runs instead of either. A name does not say what it resolves
# to. This hook refuses the act of arranging that" -- and did not check it.
# Every spelling was allowed, including that exact `kill` example.
#
# It was not hypothetical. This prefix was pasted onto shell commands through
# 2026-09-11 to keep cwd_drift_guard from seeing a `cd`: an escape hatch built
# by hand, using the one shadowing spelling that creates no file and so was
# invisible to a guard that only inspected paths.
#
# `cd` is why shutil.which() is not sufficient on its own: it is a pure
# builtin and resolves to nothing on disk.
TOOL_NAME="Bash"
COMMAND='cd() { :; }; bash .claude/hooks/tests/run-hook-tests.sh'
