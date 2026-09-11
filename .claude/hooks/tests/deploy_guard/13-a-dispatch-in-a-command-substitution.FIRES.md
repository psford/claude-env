# `echo $(gh workflow run x)` -> the hard deny still fires.
#
# The substitution runs FIRST and its output becomes echo's argument, so the
# dispatch happens whether or not anything reads the result. To the argv scan
# the only command is `echo`.
#
# Backticks are the same instruction in older clothes and must not be a second
# spelling that works -- see fixture 14.
COMMAND="echo \$(gh workflow run ios-ci.yml)"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
