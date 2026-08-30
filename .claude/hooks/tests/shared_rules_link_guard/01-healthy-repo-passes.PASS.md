# A repo whose links are healthy commits normally -> PASS.
# A guard that refuses everything is not a guard, and this is the case that
# runs on every commit forever.
setup() {
  mkdir -p .claude/rules shared/claude-md
  printf '## Shared\nInvariant rules.\n' > shared/claude-md/00-universal.md
  printf '{ "fragments": ["00-universal"], "vars": {} }\n' > .claude/claude-md.json
  printf '# Local\nrules\n' > CLAUDE.local.md
  bash /home/patrick/projects/claude-env/helpers/sync-claude-md.sh . >/dev/null 2>&1
  git add -A && git commit -qm baseline
  printf 'changed\n' > app.py && git add app.py
}
COMMAND="git commit -m 'work'"
