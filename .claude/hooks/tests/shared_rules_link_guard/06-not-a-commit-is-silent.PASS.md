# A broken repo, but the command is not a commit -> PASS.
# The guard must not fire on `git status` or `git log` in a repo it would
# otherwise refuse, or every read becomes a refusal.
setup() {
  mkdir -p .claude shared/claude-md
  printf '## Shared\nInvariant rules.\n' > shared/claude-md/00-universal.md
  printf '{ "fragments": ["00-universal"], "vars": {} }\n' > .claude/claude-md.json
  printf '# Local\nrules\n' > CLAUDE.local.md
  git add -A && git commit -qm baseline
}
COMMAND="git status --short"
