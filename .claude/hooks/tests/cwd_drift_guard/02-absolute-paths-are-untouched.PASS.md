# Doing the same work with absolute paths -> PASS.
#
# The known-negative, and the point of the whole guard: the fix is never a
# workaround, it is just absolute paths. Without this fixture a guard that
# refused every command mentioning /tmp would satisfy 01 and 03 and nothing
# would notice.
COMMAND='cp /tmp/scratch/a.json /home/patrick/projects/claude-env/b.json'
