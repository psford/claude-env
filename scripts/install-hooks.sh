#!/bin/bash
# Install git hooks for this repository
# Run this after cloning: ./scripts/install-hooks.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Installing git hooks..."

# Create pre-merge-commit hook
cat > "$HOOKS_DIR/pre-merge-commit" << 'HOOK_EOF'
#!/bin/bash
# Pre-merge hook: Block merging main into develop
# This is a safeguard against backwards merges that corrupt the git flow

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Check if we're on develop and trying to merge main
if [ "$CURRENT_BRANCH" = "develop" ]; then
    # Get the branch being merged (from MERGE_HEAD)
    if [ -f ".git/MERGE_HEAD" ]; then
        MERGE_HEAD=$(cat .git/MERGE_HEAD)
        # Check if main branch points to this commit
        MAIN_HEAD=$(git rev-parse main 2>/dev/null)
        if [ "$MERGE_HEAD" = "$MAIN_HEAD" ]; then
            echo ""
            echo "=========================================="
            echo "ERROR: Cannot merge 'main' into 'develop'"
            echo "=========================================="
            echo ""
            echo "This would corrupt the git flow. The correct direction is:"
            echo "  develop -> main (via PR)"
            echo ""
            echo "NEVER merge main into develop."
            echo ""
            echo "If you need to sync branches, the solution is:"
            echo "  1. Create PR from develop to main"
            echo "  2. Merge via GitHub web interface"
            echo ""
            echo "If main has commits not in develop (shouldn't happen):"
            echo "  1. Revert to a prior clean state"
            echo "  2. Cherry-pick specific commits if needed"
            echo ""
            exit 1
        fi
    fi
fi

exit 0
HOOK_EOF

chmod +x "$HOOKS_DIR/pre-merge-commit"
echo "  ✓ pre-merge-commit hook installed"

echo ""
echo "Git hooks installed successfully!"
echo ""
echo "Protected against:"
echo "  - Merging main into develop"
