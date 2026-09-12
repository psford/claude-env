# A new suite directory inside an EXISTING tests root -> PASS.
#
# This fixture expected BLOCK until 2026-09-11 and was wrong to. The runner
# discovers fixtures by globbing directories under its tests root, so every
# new hook needs a new directory there -- which made the repo's own fixture
# layout unreachable, once per hook, for anyone but Patrick at his own
# terminal (Grace, finding 7).
#
# The question is not "is this a new directory under tests". It is "is a test
# harness being brought into being". A tests root already holding a runner is
# an established harness; 12-... below still refuses creating a new ROOT.
TOOL_NAME="Bash"
COMMAND='mkdir -p /home/patrick/projects/claude-env/.claude/hooks/tests/brand_new_guard'
