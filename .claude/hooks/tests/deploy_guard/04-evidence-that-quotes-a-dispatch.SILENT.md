# The deadlock this fixture exists to stop, found 2026-09-11.
#
# This hook matched the RAW STRING, so it fired on any command that MENTIONED a
# dispatch -- and the thing that mentions dispatches most is the evidence
# describing the guard that stops them. The CSO gate for this repo could not
# record a verdict about ci_cost_guard, because its evidence necessarily quotes
# `gh workflow run` and `workflow_dispatch`. A hard deny, no bypass, blocking
# the one role whose job is to say whether the repo may ship.
#
# ci_cost_guard fixed the identical defect at CE-2.8. Its sibling in the same
# directory did not, until now.
COMMAND='ticket cso --sha abc123 --verdict pass --evidence "ci_cost_guard blocks gh workflow run and any workflow_dispatch trigger"'
