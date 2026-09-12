# A dispatch in backticks -> the hard deny still fires.
#
# The same act as fixture 13 with the older syntax. Listed separately because
# a fix that handles `$(` and forgets the backtick is the sibling-drift this
# repo keeps paying for -- one spelling covered, one open, and no test to say
# which.
#
# A backtick survives double quotes, so it must be seen there too.
COMMAND="echo \`gh workflow run ios-ci.yml\`"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
