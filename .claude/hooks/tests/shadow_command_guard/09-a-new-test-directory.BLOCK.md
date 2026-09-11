# `mkdir` of a test directory that does not exist yet -> BLOCK.
#
# CE-2.19 AC1 names three things: a stub on PATH, a new driver or runner, and
# a new test DIRECTORY. Only the first was implemented. The other two were
# argued away in the guard's own docstring -- "is this a test harness has no
# mechanical answer" -- and then evidence was attached to AC1 that probed the
# stub case three times and the other two clauses not at all.
#
# The general question is genuinely unanswerable. This one is not: does this
# bring into being a directory, under a tests root, that is not there yet?
TOOL_NAME="Bash"
COMMAND='mkdir -p /home/patrick/projects/claude-env/.claude/hooks/tests/brand_new_guard'
