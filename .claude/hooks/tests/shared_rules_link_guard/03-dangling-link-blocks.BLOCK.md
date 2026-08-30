# The link exists and points at nothing -> BLOCK.
# Distinct from 02: every "does .claude/rules/x.md exist" check passes here.
setup() {
  mkdir -p .claude/rules shared/claude-md
  printf '## Shared\nInvariant rules.\n' > shared/claude-md/00-universal.md
  printf '{ "fragments": ["00-universal"], "vars": {} }\n' > .claude/claude-md.json
  printf '# Local\nrules\n' > CLAUDE.local.md
  bash /home/patrick/projects/claude-env/helpers/sync-claude-md.sh . >/dev/null 2>&1
  rm .claude/rules/00-universal.md
  ln -s /nonexistent/gone.md .claude/rules/00-universal.md
  git add -A && git commit -qm baseline
  printf 'changed\n' > app.py && git add app.py
}
COMMAND="git commit -m 'work'"
