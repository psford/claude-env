# Only NEW files. Editing an existing one is ordinary work, and warning every
# time would make the warning invisible.
setup() {
  mkdir -p docs/retrospectives wwwroot/js
  cat > docs/retrospectives/2026-01-01-map-mitigations.md <<'INNER'
<!-- area-tags: js-map -->
- [ ] #3 Coordinates were assumed truthy
INNER
  printf 'export function draw() {}\n' > wwwroot/js/existing.js
  git add -A && git commit -qm "docs: retro and js"
}
TOOL_NAME="Write"
FILE_PATH="wwwroot/js/existing.js"
CONTENT="export function draw() { return 1 }"
