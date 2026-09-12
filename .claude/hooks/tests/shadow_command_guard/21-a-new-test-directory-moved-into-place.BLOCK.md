# A directory prepared elsewhere and MOVED into the tests root -> BLOCK.
#
# `mkdir /tmp/p && mv /tmp/p <tests>/brand_new_guard` creates a new
# test directory with no mkdir anywhere near the tests root. The
# directory check read mkdir only.
#
# CE-2.19, QA round 1.
TOOL_NAME="Bash"
COMMAND='mkdir /tmp/p && mv /tmp/p /home/patrick/projects/claude-env/.claude/hooks/tests/brand_new_guard'
