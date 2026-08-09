# NOT a passing test of this hook's purpose. It records that the hook CANNOT
# fire in claude-env at all.
#
# artifact_path_guard reads REGISTRY_PATH, resolved relative to its own file:
#   /home/patrick/projects/claude-env/.claude/artifact_paths.json
# That file does not exist, so load_registry() returns {} and every write
# returns 0 before any path is compared. CH-47 activated it; activation
# achieved nothing.
#
# Two consequences worth Patrick's decision (CH-58):
#   - here it is dead code that looks live
#   - the path is anchored to claude-env, so even with a registry it would
#     judge every repo's writes against claude-env's list
TOOL_NAME="Write"
FILE_PATH="docs/notes/sessionState.md"
CONTENT="## Status"
