# sessionState.md is an artifact whose claims get asserted rather than checked.
# The hook requires the file to ALREADY exist — it is about rewriting a record,
# not creating one — so the fixture has to create it first. Written without that,
# this passed as SILENT and would have recorded the hook as working.
setup() {
  printf '## Status\nprevious state\n' > sessionState.md
  git add -A && git commit -qm "chore: session state"
}
TOOL_NAME="Write"
FILE_PATH="sessionState.md"
CONTENT="## Status
Everything is deployed and verified."
EXPECT_MATCH='.'
