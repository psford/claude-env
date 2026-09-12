# Writing a driver that does not exist yet -> BLOCK.
#
# `_invoke.sh` is not a fixture that happens to be shell. It is the file
# run-hook-tests.sh delegates to, which makes it the thing that RUNS the
# tests -- the exact noun the rule blocks.
#
# The existence check is the hinge: editing a driver already on disk is
# ordinary maintenance and stays allowed (fixture 11).
TOOL_NAME="Write"
FILE_PATH="/home/patrick/projects/claude-env/.claude/hooks/tests/brand_new_guard/_invoke.sh"
CONTENT='#!/usr/bin/env bash'
