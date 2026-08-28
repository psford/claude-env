# Same behaviour spelled with a worktree and the repo runner. -> BLOCK.
TOOL_NAME="Write"
FILE_PATH="scratch/baseline_count.sh"
CONTENT='git -C "$REPO" worktree add -q --detach "$W" 56f70a1
( cd "$W" && ./run-checks.sh )'
