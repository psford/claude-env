# cd to a variable then a reader -> PASS.
#
# Reading writes nothing, wherever the command is.
COMMAND='cd "$D" && ls -la && git status'
