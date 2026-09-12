# A dispatch inside a QUOTED ssh payload -> BLOCK.
#
# Fixture 39 pins the bare spelling, `ssh host gh workflow run x`, which this
# guard already refused before CE-2.20 touched anything. The quoted spelling
# is one quote-pair away and was SILENT here while deploy_guard refused it --
# the AC4 drift QA round 2 found.
#
# The reason the two diverged: shlex keeps a quoted payload as a SINGLE token
# whose argv0 is the whole command string, so the wrapper walk steps over it.
# resolved_commands rejoins and re-reads it as shell; _classify carries a
# SECOND copy of that rejoin, and a rule written twice is how these guards
# came to disagree in the first place (Grace finding 10). This fixture is the
# pin on that copy: if it breaks, this goes red instead of going quiet.
#
# Verified RED at 3269217 (rc=0 where BLOCK expected) by QA round 3.
setup() {
  mkdir -p .github/workflows
  printf 'on: workflow_dispatch\njobs:\n  build:\n    runs-on: macos-15\n' > .github/workflows/ios.yml
  git add -A && git commit -qm wf
}
COMMAND="ssh build-box 'gh workflow run ios.yml'"
ENV_VARS=(CI_RUN_OK=1)
