#!/usr/bin/env bash
# enforce-branch-protection.sh — apply admin-enforced branch protection to the
# production branch of every psford repo.
#
# WHY: on 2026-08-07 an audit found 0 of 19 repos enforced anything against the
# owner. Sixteen had no protection at all (including photo-portfolio, live on
# psford.com); three had protection with enforce_admins=false, which exempts
# the only account that pushes. A local git hook cannot close this — the agent
# that would be blocked is the agent that can edit the hook. Server-side
# enforcement is the only real boundary.
#
# enforce_admins=true is the load-bearing setting. It rejects the ref update at
# GitHub regardless of how the push authenticated, so it covers SSH remotes
# (all of Patrick's remotes are SSH, so a scoped PAT alone does not gate push).
#
# required_approving_review_count is 0 on purpose: GitHub forbids approving
# your own PR, so requiring 1 would lock a solo owner out of their own repos.
# Zero still forces the change through a PR that Patrick merges in the browser.
#
# RUN THIS UNDER THE OLD ADMIN-CAPABLE TOKEN. The scoped fine-grained PAT
# deliberately lacks Administration:write, so --apply will fail under it. That
# is the intended end state: protection applied, then made unreachable.
#
# Usage:
#   enforce-branch-protection.sh                    # dry run, all repos
#   enforce-branch-protection.sh photo-portfolio road-trip
#   enforce-branch-protection.sh --apply <repos...> # actually write
#   enforce-branch-protection.sh --verify           # read-only audit
#
# Exit codes: 0 ok; 2 usage or missing dependency; 3 one or more repos failed.
set -uo pipefail

OWNER="${GH_OWNER:-psford}"
MODE="dry-run"
REPOS=()

for arg in "$@"; do
  case "$arg" in
    --apply)  MODE="apply" ;;
    --verify) MODE="verify" ;;
    --dry-run) MODE="dry-run" ;;
    -*) echo "enforce-branch-protection.sh: unknown flag $arg" >&2; exit 2 ;;
    *) REPOS+=("$arg") ;;
  esac
done

command -v gh >/dev/null 2>&1 || { echo "gh not found" >&2; exit 2; }

# Production branch = main, else master, else the repo default. Never assume
# "main": six repos use master and T-Tracker-Desktop defaults to develop, so a
# hardcoded name would silently skip them and report success.
production_branch() {
  local repo="$1" default="$2" heads
  heads=$(gh api "repos/$OWNER/$repo/branches" --jq '.[].name' 2>/dev/null)
  if grep -qx "main" <<<"$heads"; then echo "main"
  elif grep -qx "master" <<<"$heads"; then echo "master"
  else echo "$default"; fi
}

# Current protection state, as: <protected> <enforce_admins> <requires_pr> <reviews>
#
# The review count is reported because a PR requirement with zero required
# approvals is one the author satisfies alone. On 2026-08-09 every repo here was
# in that state: a PR was required, no review was, and the agent's token carried
# Pull requests: write -- so "only Patrick merges" was enforced by a local hook
# rather than by GitHub. GitHub refuses to let an author approve their own PR,
# which is what makes a count of 1 a real second party.
protection_state() {
  gh api "repos/$OWNER/$1/branches/$2/protection" 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except json.JSONDecodeError:
    print("none - - -"); sys.exit()
if str(d.get("status", "")) == "404":
    print("none - - -"); sys.exit()
rr = d.get("required_pull_request_reviews")
print("yes",
      "true" if d.get("enforce_admins", {}).get("enabled") else "FALSE",
      "yes" if rr else "no",
      (rr or {}).get("required_approving_review_count", 0) if rr else "-")
' 2>/dev/null || echo "unknown - - -"
}

apply_protection() {
  gh api -X PUT "repos/$OWNER/$1/branches/$2/protection" \
    -H "Accept: application/vnd.github+json" --input - >/dev/null 2>&1 <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": false
}
JSON
}

# Build the work list: explicit args, else every non-archived repo.
if [ ${#REPOS[@]} -gt 0 ]; then
  LIST=$(for r in "${REPOS[@]}"; do
    d=$(gh repo view "$OWNER/$r" --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null)
    [ -n "$d" ] && printf '%s\t%s\n' "$r" "$d" || echo "enforce-branch-protection.sh: no such repo $r" >&2
  done)
else
  LIST=$(gh repo list "$OWNER" --limit 100 --json name,defaultBranchRef,isArchived \
    --jq '.[] | select(.isArchived==false) | [.name, .defaultBranchRef.name] | @tsv' | sort)
fi

[ -n "$LIST" ] || { echo "no repos to process" >&2; exit 2; }

printf '%-22s %-8s %-22s %s\n' REPO BRANCH BEFORE ACTION
printf '%.0s-' {1..76}; echo

failed=0
while IFS=$'\t' read -r repo default; do
  [ -n "$repo" ] || continue
  branch=$(production_branch "$repo" "$default")
  read -r prot admins req_pr reviews <<<"$(protection_state "$repo" "$branch")"
  before="$prot/admins=$admins/pr=$req_pr/rev=$reviews"

  # A review count of zero is not enforcement: the author satisfies it alone.
  if [ "$prot" = "yes" ] && [ "$admins" = "true" ] && [ "$req_pr" = "yes" ] \
     && [ "$reviews" != "-" ] && [ "$reviews" -ge 1 ] 2>/dev/null; then
    printf '%-22s %-8s %-22s %s\n' "$repo" "$branch" "$before" "already enforced"
    continue
  fi

  case "$MODE" in
    verify|dry-run)
      printf '%-22s %-8s %-22s %s\n' "$repo" "$branch" "$before" \
        "$([ "$MODE" = verify ] && echo 'NEEDS ENFORCEMENT' || echo 'would apply')"
      ;;
    apply)
      if apply_protection "$repo" "$branch"; then
        read -r _ a2 r2 _rev2 <<<"$(protection_state "$repo" "$branch")"
        if [ "$a2" = "true" ]; then
          printf '%-22s %-8s %-22s %s\n' "$repo" "$branch" "$before" "APPLIED (admins=$a2 pr=$r2)"
        else
          printf '%-22s %-8s %-22s %s\n' "$repo" "$branch" "$before" "FAILED verify (admins=$a2)"
          failed=$((failed + 1))
        fi
      else
        printf '%-22s %-8s %-22s %s\n' "$repo" "$branch" "$before" "FAILED (no admin rights?)"
        failed=$((failed + 1))
      fi
      ;;
  esac
done <<<"$LIST"

echo
if [ "$MODE" = "dry-run" ]; then
  echo "Dry run only. Re-run with --apply to write, under a token that still has Administration:write."
fi
[ "$failed" -eq 0 ] || { echo "$failed repo(s) failed" >&2; exit 3; }
