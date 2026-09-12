# Adding a case to an existing suite, by relative path -> PASS.
#
# The same resolution question as fixture 22, asked about the case the rule
# explicitly protects: "Adding test CASES to a suite that already exists is
# normal work." A guard that answers it against the wrong directory decides
# the suite does not exist and refuses ordinary work.
#
# The refuse direction cannot be used to pin this defect. Under a guard
# resolving against its own process directory, a relative path to something
# genuinely new lands where nothing exists and is refused -- the same verdict
# the correct guard reaches, for a different reason. Measured both ways
# before this fixture was written; only the allow direction separates them.
setup() {
  mkdir -p .claude/hooks/tests/existing_suite
  printf '#!/usr/bin/env bash\n' > .claude/hooks/tests/existing_suite/_invoke.sh
  git add -A && git commit -qm "chore: a suite that already exists"
}
TOOL_NAME="Bash"
COMMAND='printf x > .claude/hooks/tests/existing_suite/99-a-new-case.BLOCK.md'
