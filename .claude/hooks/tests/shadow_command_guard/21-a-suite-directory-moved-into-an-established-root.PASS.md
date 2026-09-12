# The same, spelled with mv rather than mkdir -> PASS.
#
# Also expected BLOCK until 2026-09-11. A directory prepared elsewhere and
# moved into an established tests root is the same ordinary act as making it
# there, and refusing it was the same over-refusal.
#
# The mv spelling still matters: 24-... refuses it when the destination is a
# tests ROOT that does not exist.
TOOL_NAME="Bash"
COMMAND='mkdir /tmp/prepared_suite && mv /tmp/prepared_suite /home/patrick/projects/claude-env/.claude/hooks/tests/moved_guard'
