# Same behaviour in shell: worktree, sed -i into it, then the repo runner.
# -> BLOCK.
TOOL_NAME="Write"
FILE_PATH="scratch/sweep.sh"
CONTENT='git -C "$REPO" worktree add -q --detach "$W" 56f70a1
sed -i "s/old/new/" "$W/cli/ticket.py"
( cd "$W" && ./run-checks.sh )'
