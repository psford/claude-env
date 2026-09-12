# A dispatch inside a `bash -c` payload -> the hard deny still fires.
#
# ci_cost_guard learned to descend into payloads at CH-237.10 (its fixture 29)
# and deploy_guard never did -- the sibling-drift this repo keeps paying for.
# CE-2.20's first parser made it worse: the raw string match had at least seen
# the words, and reading argv0 as `bash` saw nothing at all.
#
# Real bash runs the payload. The guard reads it.
COMMAND="bash -c 'gh workflow run ios-ci.yml'"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
