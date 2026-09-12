# The LONG spelling of `-S`. The short one was enumerated; this one was not, and coreutils runs both.
#
# CE-2.20, QA round 2. Round 0 was wrappers, round 1 was shell syntax,
# and this is round 3: indirection. Each round was a construct absent
# from a finite list of known hiding places, which is why that list was
# replaced by the opposite question -- authority is granted only to text
# that is plainly commands and separators.
COMMAND='env --split-string '\''gh workflow run ios.yml'\'''
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
