# Copy + run with NOTHING edited is MEASUREMENT -- what did the suite look like
# at an older commit. Refusing this was the corner CE-2.5 removed. -> PASS.
TOOL_NAME="Write"
FILE_PATH="scratch/baseline_count.sh"
CONTENT='git -C "$REPO" worktree add -q --detach "$W" 56f70a1
( cd "$W" && ./run-checks.sh | grep -oE "Ran [0-9]+ tests?" )
git -C "$REPO" worktree remove --force "$W"'
