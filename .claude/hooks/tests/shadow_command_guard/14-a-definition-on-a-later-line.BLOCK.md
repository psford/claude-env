# A definition after a NEWLINE -> BLOCK.
#
# `true; cd() { :; }` was refused and `set -e\ncd() { :; }` was not --
# the same definition, differing only in the character in front of it.
# The separator class had `;&|{` and no newline, and a multiline command
# is the normal shape here, so the guard refused the spelling nobody
# uses and allowed the one everybody does.
#
# CE-2.19, QA round 1.
TOOL_NAME="Bash"
COMMAND='set -e
cd() { :; }'
