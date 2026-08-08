# An apostrophe plus the words git and push tripped the fail-closed branch. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND="gh pr create --body \"claude-env now uses the git-flow-trunk fragment. Also corrects that fragment's stale carve-out, untrue now that enforce_admins=true rejects every direct push.\""
