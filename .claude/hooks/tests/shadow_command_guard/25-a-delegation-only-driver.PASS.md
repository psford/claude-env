# A three-line driver that only execs a shared one -> PASS.
#
# `_invoke.sh` is in DRIVER_NAMES because a driver is what it usually is. The
# established shape here is a delegation: the runner already exists and is
# being pointed at, and calling that "bringing a runner into being" is not
# true (Grace, finding 7). Every suite in this directory has one.
TOOL_NAME="Write"
FILE_PATH="/home/patrick/projects/claude-env/.claude/hooks/tests/brand_new_guard/_invoke.sh"
CONTENT='#!/usr/bin/env bash
exec "$(dirname "$0")/../_exitcode_driver.sh" "$@"'
