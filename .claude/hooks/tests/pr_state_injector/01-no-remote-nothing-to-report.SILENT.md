# Records a DEPENDENCY, not a success. In a repo with no GitHub remote the hook
# has no PR state to inject and stays quiet.
#
# Its FIRES case is deliberately absent: firing requires a real GitHub remote and
# an authenticated `gh`, i.e. network and credentials. A fixture that needs those
# is a fixture that fails on a plane and gets deleted, so the coverage limit is
# recorded here instead.
#
# It is not unobserved. This hook emitted "PR STATE" on essentially every git
# command throughout 2026-08-09 in claude-harness and claude-env — including the
# MANDATORY PR CHECK that stopped a merged PR being described as if it were open.
# That is live evidence, and it is a weaker claim than a fixture; saying so is
# the point.
COMMAND='git status'
