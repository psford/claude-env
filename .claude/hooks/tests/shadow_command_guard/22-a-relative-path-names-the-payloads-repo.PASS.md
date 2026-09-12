# A relative path resolves against the payload's repo -> PASS.
#
# The driver invokes this hook from a third directory, so the hook process's
# own location and the repo the command is about are different places. That
# is the whole point: `_invoke.sh` below exists in the scratch repo the
# payload names, and nowhere near where the hook is running.
#
# A guard resolving against its own process directory finds nothing there,
# concludes the driver does not exist yet, and refuses -- which is how the
# same command reached opposite verdicts in two repos before 82d9609.
#
# Every one of this hook's other fixtures uses an ABSOLUTE path, which
# resolves identically under either base, so reverting resolve() to
# os.path.abspath left all twenty-one of them green. This one goes red.
setup() {
  mkdir -p .claude/hooks/tests/existing_suite
  printf '#!/usr/bin/env bash\n' > .claude/hooks/tests/existing_suite/_invoke.sh
  git add -A && git commit -qm "chore: a suite that already exists"
}
TOOL_NAME="Bash"
COMMAND='cp /dev/null .claude/hooks/tests/existing_suite/_invoke.sh'
