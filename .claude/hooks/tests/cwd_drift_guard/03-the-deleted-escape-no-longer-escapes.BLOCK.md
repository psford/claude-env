# The old escape token, still refused -> BLOCK.
#
# This is the fixture that actually pins CE-12.1. Fixtures 01 and 02 do not:
# 01's command carries no token, so the guard that STILL HAD the escape
# blocked it too, and a fixture that passes at both commits pins nothing.
#
# This one is red against the guard as it shipped before 2026-09-13, because
# there the token was read first and returned 0 -- the command was allowed,
# and the refusal helpfully printed the token to anyone who hit it.
#
# Two spellings, because deleting the ESCAPE constant is not enough on its
# own: the token as a trailing comment, and the token as an environment
# assignment in front of the command. The second was still allowed after the
# constant was deleted, for an unrelated reason -- CD_OUTSIDE required `cd`
# at a statement boundary and an assignment prefix is not one, so ANY prefix
# walked past it (`FOO=1 cd /tmp/x`, `sudo cd /tmp/x`). The token happened to
# be a valid assignment name, so the escape kept working by accident after it
# had been removed on purpose.
COMMAND='CWD_DRIFT_OK=1 cd /tmp/scratch && ls'
