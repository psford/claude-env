# `ssh host 'gh workflow run x'` -> the hard deny still fires.
#
# Fixture 08 caught the BARE spelling. QA broke it by adding one quote pair:
# shlex keeps a quoted remote command as a SINGLE token, so argv0 became the
# whole string `gh workflow run ios-ci.yml` rather than `gh`, and the wrapper
# walk -- which had just been taught about ssh -- handed it straight past.
#
# The two spellings are one instruction. ssh joins its operands and the REMOTE
# shell parses them, so the runner rejoins and re-reads them as shell rather
# than treating them as an argv.
#
# This is why fixture 08 alone was not enough: it pinned the wrapper, not the
# thing the wrapper carries.
COMMAND="ssh build-box 'gh workflow run ios-ci.yml'"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
