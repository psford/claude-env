# A broken repo with the old escape token in the command -> BLOCK.
#
# CE-12.8. This was 07-escape-hatch-passes: the guard waived itself for any
# command whose text held the token below, and printed that token in both of
# its refusals. Zero trust allows no override an agent can type, so the token
# is gone and this commit is refused like any other. The case stays as the
# pin that the token means nothing now.
setup() {
  mkdir -p .claude shared/claude-md
  printf '## Shared\nInvariant rules.\n' > shared/claude-md/00-universal.md
  printf '{ "fragments": ["00-universal"], "vars": {} }\n' > .claude/claude-md.json
  printf '# Local\nrules\n' > CLAUDE.local.md
  git add -A && git commit -qm baseline
  printf 'changed\n' > app.py && git add app.py
}
COMMAND="SHARED_RULES_OK=1 git commit -m 'deliberate'"
