# Redirecting output into a scratch file whose basename is a command -> PASS.
#
# A shadow is a file that will be EXECUTED instead of the real command. A
# file of the same name that nothing can run is not a shadow of anything --
# but this guard refused every one of them, and the scratchpad lives outside
# any work tree by the harness's own instruction, so the work-tree escape
# never applied. env, diff, stat, sort, id and test are ordinary names for a
# scratch file, and writing one was a wall with no bypass (Grace, finding 6).
#
# Fixture 01 is the control: a shebang plus chmod plus a PATH prepend is
# still refused, so requiring runnability tightened the true positive.
TOOL_NAME="Bash"
COMMAND='env > /tmp/scratch/env'
