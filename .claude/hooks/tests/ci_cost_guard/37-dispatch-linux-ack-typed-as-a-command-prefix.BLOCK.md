# `CI_RUN_OK=1 <command>` typed as a PREFIX -> still BLOCK.
#
# CH-237.10, the deadlock half. The metered-dispatch refusal used to print
# `CI_RUN_OK=1 <command>` while the code read os.environ, and a hook cannot
# see a per-command prefix -- the instruction could not be followed by
# anyone. Fixture 03 hides this by exporting the variable to the hook
# process. The fix changed the message to name what works (exported in the
# shell that LAUNCHES Claude Code); it did NOT start reading the prefix,
# because an in-command ack would be an agent-usable bypass. This fixture
# pins that: the prefix is stripped as a mere assignment and satisfies
# nothing. Green before AND after, on purpose -- it exists so nobody later
# "fixes" the message by adding the hatch.
setup() {
  mkdir -p .github/workflows
  printf 'on: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n' > .github/workflows/ci.yml
  git add -A && git commit -qm wf
}
COMMAND="CI_RUN_OK=1 gh workflow run ci.yml"
