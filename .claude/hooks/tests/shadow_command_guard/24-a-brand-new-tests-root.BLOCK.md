# Creating a tests ROOT that does not exist -> BLOCK.
#
# The line finding 7 draws. Adding a suite to a harness that already exists
# is ordinary work; calling a harness into being where there was none is the
# act the rule blocks. /tmp/newproj has no runner anywhere above it.
TOOL_NAME="Bash"
COMMAND='mkdir -p /tmp/newproj/tests/first_suite'
