# A definition inside `$( )` -> BLOCK.
#
# An open paren is a command position too. The substitution is not
# quoted, so the text survives the mask; only the separator class was
# missing it.
#
# CE-2.19, QA round 1.
TOOL_NAME="Bash"
COMMAND='echo $(cd() { :; })'
