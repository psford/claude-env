# Committing in a directory outside any git repository: the branch cannot be
# determined, so it might be main and we cannot prove otherwise. -> BLOCK.
#
# The directory must be outside the scratch repo -- a subdirectory of it still
# resolves a branch, because git walks up to the enclosing work tree.
setup() {
  mkdir -p /tmp/claude-hook-test-notarepo
}
COMMAND="cd /tmp/claude-hook-test-notarepo && git commit -m x"
