# The case it exists for, and only reachable since CH-58: the registry now comes
# from the repo being written to, so a fixture can supply one.
setup() {
  mkdir -p .claude docs/notes
  cat > .claude/artifact_paths.json <<'INNER'
{"artifacts": [{"name": "sessionState", "canonical_path": "sessionState.md"}]}
INNER
  printf '## Status\n' > sessionState.md
  git add -A && git commit -qm "chore: registry and artifact"
}
TOOL_NAME="Write"
FILE_PATH="docs/notes/sessionState.md"
CONTENT="## Status"
EXPECT_MATCH='WRONG PATH|ARTIFACT PATH'
