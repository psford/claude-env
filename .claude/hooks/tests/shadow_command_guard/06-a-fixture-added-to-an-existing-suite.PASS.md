# Adding a case to a suite that already exists is explicitly normal work under
# the very rule this guard enforces -> PASS.
#
# Twelve of these landed on 2026-09-11 and should have. A control that cannot
# tell them from a new driver would be routed around within a day, which is
# worse than no control at all.
TOOL_NAME="Write"
FILE_PATH="/home/patrick/projects/claude-env/.claude/hooks/tests/ci_cost_guard/99-a-new-case.BLOCK.md"
CONTENT='COMMAND="a dispatch"'
