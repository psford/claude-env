# `(gh workflow run x)` -> the hard deny still fires.
#
# QA, 2026-09-11, on CE-2.20's second attempt. A subshell tokenises perfectly:
# shlex hands back `(gh`, `workflow`, `run`, `x)` and argv0 is `(gh`, which is
# not `gh`. The walk found nothing and REPORTED that it had parsed, so the
# fail-closed fallback stayed quiet -- denied before the fix, silent after.
#
# The lesson is the fix: parsing is not the same as understanding. A construct
# the walk cannot see into means the walk is not authoritative, whatever it
# managed to tokenise.
COMMAND="(gh workflow run ios-ci.yml)"
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
