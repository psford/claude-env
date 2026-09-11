# Editing a driver that is already on disk -> PASS.
#
# The specificity control for 09 and 10. If the new clauses fired on any path
# that looks like test infrastructure, they would block the maintenance of
# every driver in this suite, and the block would be routed around inside a
# day -- which fixture 06 already records as worse than no control at all.
#
# What is blocked is calling a runner into BEING, not touching one that is
# already there.
TOOL_NAME="Write"
FILE_PATH="/home/patrick/projects/claude-env/.claude/hooks/tests/ci_cost_guard/_invoke.sh"
CONTENT='#!/usr/bin/env bash'
