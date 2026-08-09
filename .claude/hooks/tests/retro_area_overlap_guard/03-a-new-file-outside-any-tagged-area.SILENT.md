# A new file nowhere near a tagged area. No overlap, nothing to say.
setup() {
  mkdir -p docs/retrospectives
  cat > docs/retrospectives/2026-01-01-map-mitigations.md <<'INNER'
<!-- area-tags: js-map -->
- [ ] #3 Coordinates were assumed truthy
INNER
  git add -A && git commit -qm "docs: retro"
}
TOOL_NAME="Write"
FILE_PATH="docs/notes/agenda.md"
CONTENT="# Agenda"
