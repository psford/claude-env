# A command that merely NAMES opening a PR is not opening one -> PASS.
#
# CE-2.20. This hook asked `gh ... pr ... create` of the raw command string, so
# a ticket titled after the rule, a commit message describing it, or a CSO's
# evidence about this very guard all read as the act. deploy_guard's version of
# the same defect deadlocked the release gate outright, which is how the class
# was finally swept.
#
# The guard also had NO fixtures before this one -- it shipped unobserved, like
# deploy_guard did.
COMMAND='ticket new --type chore --title "open the PR only after gh pr create is gated"'
