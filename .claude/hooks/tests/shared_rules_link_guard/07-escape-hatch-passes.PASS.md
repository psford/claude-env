# A broken repo with the documented escape in the command -> PASS.
# The hatch exists and the refusal names it. A gate claiming to be
# unbypassable teaches people to hunt for the bypass and stop reading.
setup() {
  mkdir -p .claude shared/claude-md
  printf '## Shared\nInvariant rules.\n' > shared/claude-md/00-universal.md
  printf '{ "fragments": ["00-universal"], "vars": {} }\n' > .claude/claude-md.json
  printf '# Local\nrules\n' > CLAUDE.local.md
  git add -A && git commit -qm baseline
  printf 'changed\n' > app.py && git add app.py
}
COMMAND="SHARED_RULES_OK=1 git commit -m 'deliberate'"
