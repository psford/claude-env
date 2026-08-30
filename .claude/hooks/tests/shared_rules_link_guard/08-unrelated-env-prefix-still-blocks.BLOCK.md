# A broken repo committed with an UNRELATED env prefix -> BLOCK.
#
# This is the fixture the escape-hatch control should have had. Case 07 passed
# whether or not the escape hatch worked, because `VAR=1 git commit` was not
# recognised as a commit at all: shlex puts the assignment in tokens[0], the
# git check failed, and the guard returned 0 before ever looking at the repo.
#
# So the hatch was not what let 07 through, and any env prefix at all was a
# silent bypass. Removing the escape hatch changed nothing and the control
# survived, which is what surfaced it.
setup() {
  mkdir -p .claude shared/claude-md
  printf '## Shared\nInvariant rules.\n' > shared/claude-md/00-universal.md
  printf '{ "fragments": ["00-universal"], "vars": {} }\n' > .claude/claude-md.json
  printf '# Local\nrules\n' > CLAUDE.local.md
  git add -A && git commit -qm baseline
  printf 'changed\n' > app.py && git add app.py
}
COMMAND="GIT_AUTHOR_NAME=someone git commit -m 'work'"
