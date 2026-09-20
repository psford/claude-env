#!/usr/bin/env bash
# new-dev-worktree.sh — create a dev/<ticket-id> worktree that comes out
# inheriting the shared rules, in one step.
#
# THE FAILURE THIS EXISTS FOR (CE-2.50).
#
# A dev worktree created with a bare `git worktree add` does not inherit
# claude-env's shared rules: .claude/rules/*.md is gitignored here (a
# blanket `*.md` rule with no carve-out for it, unlike claude-harness where
# those paths ARE tracked), so `git worktree add` checks out nothing under
# .claude/rules/ at all. Nobody finds out until `shared_rules_link_guard`
# refuses the first commit — after the story's work is already done.
#
# helpers/sync-claude-md.sh already writes the links and already has a
# --check mode. The missing piece was a single command that creates the
# worktree AND runs it, so there is never a window where the worktree
# exists but is not yet linked.
#
# Usage:
#   new-dev-worktree.sh <repo-dir> <ticket-id> [base-ref]
#     Creates <parent-of-repo-dir>/<repo-name>--<ticket-id> on a new branch
#     dev/<ticket-id>, branched from [base-ref] (default: develop), then
#     runs sync-claude-md.sh on it. Sibling-of-claude-env placement matches
#     the convention every other dev worktree already uses.
#
#   new-dev-worktree.sh --check <worktree-dir>
#     Points sync-claude-md.sh --check at an EXISTING worktree — including
#     one made by a bare `git worktree add` — so it can be verified before
#     any work happens in it, not only when a commit is attempted.
#
# Exit codes: 0 ok; 2 usage or git error; 3 worktree created but the shared
# rules could not be linked (claude-md.json missing is not an error — that
# repo has not opted in — but a link failure after opting in is).
set -uo pipefail

# sync-claude-md.sh always ships beside this script, in the same helpers/
# directory -- resolved from OUR location, not from CLAUDE_ENV_ROOT, which
# is a var sync-claude-md.sh itself reads (for where the FRAGMENTS live) and
# which this script must not need in order to find the sync script itself.
# Any CLAUDE_ENV_ROOT set in the environment still reaches sync-claude-md.sh
# below, since a plain `bash "$SYNC" ...` inherits it like any other var.
SYNC="$(cd "$(dirname "$0")" && pwd)/sync-claude-md.sh"

usage() {
  echo "usage: new-dev-worktree.sh <repo-dir> <ticket-id> [base-ref]" >&2
  echo "       new-dev-worktree.sh --check <worktree-dir>" >&2
  exit 2
}

if [ "$#" -eq 2 ] && [ "$1" = "--check" ]; then
  target="$2"
  if [ ! -f "$target/.claude/claude-md.json" ]; then
    echo "new-dev-worktree.sh: $target has no .claude/claude-md.json — not opted into the shared rules"
    exit 0
  fi
  exec bash "$SYNC" --check "$target"
fi

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
  usage
fi

REPO_DIR="$1"
TICKET_ID="$2"
BASE_REF="${3:-develop}"

if ! git -C "$REPO_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "new-dev-worktree.sh: $REPO_DIR is not a git repo" >&2
  exit 2
fi
REPO_DIR="$(git -C "$REPO_DIR" rev-parse --show-toplevel)"

PARENT_DIR="$(dirname "$REPO_DIR")"
REPO_NAME="$(basename "$REPO_DIR")"
WORKTREE_DIR="$PARENT_DIR/$REPO_NAME--$TICKET_ID"
BRANCH="dev/$TICKET_ID"

if [ -e "$WORKTREE_DIR" ]; then
  echo "new-dev-worktree.sh: $WORKTREE_DIR already exists" >&2
  exit 2
fi

if ! git -C "$REPO_DIR" worktree add -b "$BRANCH" "$WORKTREE_DIR" "$BASE_REF"; then
  echo "new-dev-worktree.sh: git worktree add failed" >&2
  exit 2
fi

if [ ! -f "$WORKTREE_DIR/.claude/claude-md.json" ]; then
  echo "new-dev-worktree.sh: created $WORKTREE_DIR on branch $BRANCH"
  echo "  no .claude/claude-md.json there, so it does not consume shared rules — nothing to link."
  exit 0
fi

if [ ! -f "$SYNC" ]; then
  echo "new-dev-worktree.sh: created $WORKTREE_DIR on branch $BRANCH, but" >&2
  echo "  $SYNC is missing so the shared-rules links could not be written." >&2
  exit 3
fi

if ! bash "$SYNC" "$WORKTREE_DIR"; then
  echo "new-dev-worktree.sh: created $WORKTREE_DIR on branch $BRANCH, but" >&2
  echo "  sync-claude-md.sh failed to link it — see output above." >&2
  exit 3
fi

if ! bash "$SYNC" --check "$WORKTREE_DIR" >&2; then
  echo "new-dev-worktree.sh: created $WORKTREE_DIR on branch $BRANCH, but" >&2
  echo "  it still fails sync-claude-md.sh --check after linking — see above." >&2
  exit 3
fi

echo "new-dev-worktree.sh: $WORKTREE_DIR is ready on branch $BRANCH, inheriting the shared rules."
