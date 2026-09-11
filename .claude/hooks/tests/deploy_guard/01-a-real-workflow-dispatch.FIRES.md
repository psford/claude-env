# An actual dispatch -> the hard deny fires.
#
# The standing ruling it enforces: Claude never triggers a workflow run;
# Patrick does it from the Actions web UI. This is the case the guard exists
# for and it must keep working after the parser change.
COMMAND="gh workflow run ios-ci.yml"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
