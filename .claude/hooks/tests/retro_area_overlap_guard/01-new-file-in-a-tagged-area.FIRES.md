# Writing a NEW file in an area that still has open retrospective mitigations:
# the case it exists for — you are about to repeat something already learned.
setup() {
  mkdir -p docs/retrospectives wwwroot/js
  cat > docs/retrospectives/2026-01-01-map-mitigations.md <<'INNER'
<!-- area-tags: js-map -->
- [ ] #3 Coordinates were assumed truthy
- [x] #4 Already handled
INNER
  git add -A && git commit -qm "docs: retro"
}
TOOL_NAME="Write"
FILE_PATH="wwwroot/js/newlayer.js"
CONTENT="export function draw() {}"
EXPECT_MATCH='mitigation|retrospective'
