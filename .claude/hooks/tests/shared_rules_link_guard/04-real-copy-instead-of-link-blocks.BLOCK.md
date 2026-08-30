# A real file with IDENTICAL content where the link belongs -> BLOCK.
# The case that matters most and the one an existence check cannot see:
# identical bytes today is what drift looks like the moment before it starts.
setup() {
  mkdir -p .claude/rules shared/claude-md
  printf '## Shared\nInvariant rules.\n' > shared/claude-md/00-universal.md
  printf '{ "fragments": ["00-universal"], "vars": {} }\n' > .claude/claude-md.json
  printf '# Local\nrules\n' > CLAUDE.local.md
  bash /home/patrick/projects/claude-env/helpers/sync-claude-md.sh . >/dev/null 2>&1
  rm .claude/rules/00-universal.md
  cp shared/claude-md/00-universal.md .claude/rules/00-universal.md
  git add -A && git commit -qm baseline
  printf 'changed\n' > app.py && git add app.py
}
COMMAND="git commit -m 'work'"
