# `ssh host gh workflow run` -> the hard deny still fires.
#
# The second half of the CSO's finding. Which machine holds the `gh` client
# changes nothing: the workflow runs on GitHub and the minutes bill to the
# same account. A guard that reads only the local argv0 sees `ssh` and stops.
#
# ssh's destination is an operand, not a flag, so the wrapper walk has to
# consume exactly one bare word before the real command starts -- the same
# shape as timeout's DURATION, and the reason each wrapper carries its own
# option grammar instead of a shared guess.
COMMAND="ssh build-box gh workflow run ios-ci.yml"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
