#!/usr/bin/env bash
# park-work.sh <slug> [message]
#
# Snapshots the ENTIRE working tree (tracked modifications/deletions +
# untracked files, respecting .gitignore) into a standalone WIP commit
# under refs/parked/<date>-<slug>.
#
# Does NOT touch HEAD, the current branch, the real index, or the working
# tree — it builds the tree object via a scratch index (GIT_INDEX_FILE),
# so it is safe to run before an otherwise-destructive discard, and safe
# to run repeatedly. After parking, proceed with the discard normally.
#
# Recover later with:
#   git checkout -b recovered-<slug> refs/parked/<date>-<slug>
# Inspect without checking out:
#   git show refs/parked/<date>-<slug> --stat
# List all parked snapshots:
#   git for-each-ref refs/parked
# Delete one once it's no longer needed:
#   git update-ref -d refs/parked/<date>-<slug>
set -euo pipefail

usage() { echo "Usage: park-work.sh <slug> [message]" >&2; exit 1; }
[ $# -ge 1 ] || usage
SLUG="$1"; shift || true
MSG="${*:-WIP parked snapshot}"

if ! [[ "$SLUG" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "park-work: slug must be lowercase alnum/dashes (got: $SLUG)" >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

DATE="$(date +%Y-%m-%d)"
REF="refs/parked/${DATE}-${SLUG}"

if git show-ref --verify --quiet "$REF"; then
  echo "park-work: $REF already exists. Use a different slug or delete it first:" >&2
  echo "  git update-ref -d $REF" >&2
  exit 1
fi

HEAD_SHA="$(git rev-parse HEAD)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

# Build a fresh scratch index reflecting exactly the current working tree
# (tracked+modified+untracked, minus .gitignored) without touching the
# real index. Deleted-in-worktree tracked files are correctly omitted
# because the scratch index starts empty — nothing is carried over from
# HEAD/the real index unless `git add` puts it there.
SCRATCH_INDEX="$(mktemp)"
trap 'rm -f "$SCRATCH_INDEX"' EXIT
# mktemp pre-creates an empty regular file, but git treats an existing
# zero-byte file as a corrupt index ("index file smaller than expected")
# rather than building a fresh one. Remove it so git starts clean; the
# trap still cleans up whatever git writes at this path on exit.
rm -f "$SCRATCH_INDEX"
export GIT_INDEX_FILE="$SCRATCH_INDEX"
git add -A -- .
TREE_SHA="$(git write-tree)"
unset GIT_INDEX_FILE

if [ "$TREE_SHA" = "$(git rev-parse "HEAD^{tree}")" ]; then
  echo "park-work: nothing to park — working tree matches HEAD exactly." >&2
  exit 1
fi

STAT="$(git diff --stat HEAD -- . 2>/dev/null | tail -1)"
FULL_MSG="$(printf '%s\n\nparked-from: %s\nparked-at: %s\nworking-tree-diffstat: %s\n' \
  "$MSG" "$BRANCH" "$(date -Iseconds)" "${STAT:-untracked-only}")"

COMMIT_SHA="$(git commit-tree "$TREE_SHA" -p "$HEAD_SHA" -m "$FULL_MSG")"
git update-ref "$REF" "$COMMIT_SHA"

echo "park-work: parked working tree to $REF"
echo "  commit: $COMMIT_SHA"
echo "  recover:  git checkout -b recovered-${SLUG} $REF"
echo "  inspect:  git show $REF --stat"
echo "  working tree / index / HEAD were NOT modified — proceed with your discard."
