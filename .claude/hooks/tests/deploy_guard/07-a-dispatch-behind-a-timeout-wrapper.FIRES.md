# `timeout 900 gh workflow run` -> the hard deny still fires.
#
# The CSO gate caught this on 2026-09-11. CE-2.20's first parser read argv0
# only, so the raw-text match it replaced DENIED this and the token version
# let it through silently -- a metered macOS dispatch with no gate anywhere.
# Trading a false positive for a false negative is not a fix.
#
# `timeout` is not a hypothetical here: it is this box's own incident wrapper.
# The 2026-09-10 orphan leak was `timeout 900 claude -p`, so it is the prefix
# most likely to be in front of a long-running command on this machine.
COMMAND="timeout 900 gh workflow run ios-ci.yml"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
