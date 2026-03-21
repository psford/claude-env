#!/usr/bin/env bash
# Install git hooks into the ~/.claude git repo to prevent Windows path
# contamination from being committed to the claude-config remote.
#
# Usage: bash infrastructure/wsl/install-claude-config-hooks.sh

set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
HOOKS_DIR="${CLAUDE_DIR}/.git/hooks"
HOOK_FILE="${HOOKS_DIR}/pre-commit"

if [ ! -d "${CLAUDE_DIR}/.git" ]; then
    echo "ERROR: ${CLAUDE_DIR} is not a git repository."
    echo "       Run wsl-setup.sh first to clone claude-config."
    exit 1
fi

mkdir -p "$HOOKS_DIR"

cat > "$HOOK_FILE" << 'HOOK_EOF'
#!/usr/bin/env bash
# Blocks commits containing Windows absolute paths in JSON files.
set -euo pipefail

WIN_PATH_PATTERN='[A-Za-z]:\\{1,2}[A-Za-z]'

staged_json=$(git diff --cached --name-only --diff-filter=ACM | grep '\.json$' || true)

if [ -z "$staged_json" ]; then
    exit 0
fi

found=0
while IFS= read -r file; do
    matches=$(git show ":${file}" 2>/dev/null | grep -nP "${WIN_PATH_PATTERN}" || true)
    if [ -n "$matches" ]; then
        found=1
        echo "BLOCKED: Windows path in ${file}:"
        echo "$matches" | head -5
        echo ""
    fi
done <<< "$staged_json"

if [ "$found" -eq 1 ]; then
    echo "Windows paths break plugin loading in WSL2."
    echo "Unstage registry files or fix the paths."
    exit 1
fi
exit 0
HOOK_EOF

chmod +x "$HOOK_FILE"

echo "Installed pre-commit hook at: ${HOOK_FILE}"
if bash -n "$HOOK_FILE"; then
    echo "Hook syntax: OK"
else
    echo "ERROR: Hook has a syntax error"
    exit 1
fi
