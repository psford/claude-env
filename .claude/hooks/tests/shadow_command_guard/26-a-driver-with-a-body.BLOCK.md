# A driver that does its own work -> BLOCK.
#
# The specificity control for 25. The exemption is for a delegation, not for
# anything named _invoke.sh: a file with a real body is a runner being
# written, which is the act that needs Patrick's approval first.
TOOL_NAME="Write"
FILE_PATH="/home/patrick/projects/claude-env/.claude/hooks/tests/brand_new_guard/_invoke.sh"
CONTENT='#!/usr/bin/env bash
for fixture in "$@"; do
  printf "%s\\n" "$fixture"
  python3 ./hook.py < "$fixture"
done'
