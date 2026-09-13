# `cd` into a scratch directory -> BLOCK.
#
# The case the guard exists for. The harness resets the shell to the primary
# working directory when a command leaves the allowed set, so the NEXT command
# runs against the wrong repo and the error never mentions directories. On
# 2026-08-24 that produced "no such ticket" for a ticket that existed, and a
# commit landing in the wrong repository.
#
# This guard shipped with NO fixtures, which is how it carried a live escape
# hatch for weeks without anything noticing.
COMMAND='cd /tmp/scratch && ls'
