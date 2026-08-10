# Writing the artifact where the registry says it belongs is the whole point.
setup() {
  mkdir -p .claude
  cat > .claude/artifact_paths.json <<'INNER'
{"artifacts": [{"name": "sessionState", "canonical_path": "sessionState.md"}]}
INNER
  printf '## Status\n' > sessionState.md
  git add -A && git commit -qm "chore: registry and artifact"
}
TOOL_NAME="Write"
FILE_PATH="sessionState.md"
CONTENT="## Status
updated"
