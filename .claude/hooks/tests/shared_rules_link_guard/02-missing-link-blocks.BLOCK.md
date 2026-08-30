# The link was never created -> BLOCK. The repo inherits nothing while looking
# exactly like a healthy one, which is the quiet failure this guard exists for.
setup() {
  mkdir -p .claude shared/claude-md
  printf '## Shared\nInvariant rules.\n' > shared/claude-md/00-universal.md
  printf '{ "fragments": ["00-universal"], "vars": {} }\n' > .claude/claude-md.json
  printf '# Local\nrules\n' > CLAUDE.local.md
  git add -A && git commit -qm baseline
  printf 'changed\n' > app.py && git add app.py
}
COMMAND="git commit -m 'work'"
