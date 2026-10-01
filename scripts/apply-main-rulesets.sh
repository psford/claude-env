#!/usr/bin/env bash
# Apply the main-protection ruleset to every develop->main repo (todo #2,
# branch protection: robot merges develop, Patrick merges main).
#
# MUST run as an account with admin on psford/* (Patrick) — the robot
# account cannot create rulesets (404, no admin scope, by design).
#
# Per repo this creates/updates a ruleset "main-protected":
#   - target: refs/heads/main, enforcement: active
#   - rules:  require a PR (1 approving review, stale reviews dismissed),
#             no force pushes, no deletions
#   - bypass: psford (uid 10429335) only — the emergency-hotfix exception
#
# Effect: the robot can never land main alone (cannot self-approve);
# releases are robot-opened develop->main PRs that Patrick approves and
# merges on the web; Patrick retains direct-push for hotfixes.
#
# Usage:  gh auth as psford, then:  bash apply-main-rulesets.sh [repo ...]
#         default repos = the eight documented develop->main repos
set -euo pipefail

OWNER="${OWNER:-psford}"
PSFORD_UID=10429335
DEFAULT_REPOS=(gpu-crash-analyzer nfl-stats omni-map road-trip stock-analyzer whisper-service T-Tracker-Desktop claude-env)

repos=("$@")
[ ${#repos[@]} -eq 0 ] && repos=("${DEFAULT_REPOS[@]}")

payload() {
    cat <<EOF
{
  "name": "main-protected",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 1,
      "dismiss_stale_reviews_on_push": true,
      "require_code_owner_review": false,
      "require_last_push_approval": false
    }}
  ],
  "bypass_actors": [{"actor_id": ${PSFORD_UID}, "actor_type": "User"}]
}
EOF
}

for repo in "${repos[@]}"; do
    echo "==> ${OWNER}/${repo}"
    existing_id=$(gh api "repos/${OWNER}/${repo}/rulesets" --jq '.[] | select(.name=="main-protected") | .id' 2>/dev/null || true)
    if [ -n "$existing_id" ]; then
        echo "    ruleset exists (id ${existing_id}) — updating"
        gh api -X PUT "repos/${OWNER}/${repo}/rulesets/${existing_id}" --input - <<<"$(payload)" >/dev/null
    else
        gh api -X POST "repos/${OWNER}/${repo}/rulesets" --input - <<<"$(payload)" >/dev/null
    fi
    # verify what the server now enforces
    gh api "repos/${OWNER}/${repo}/rulesets" \
        --jq '.[] | select(.name=="main-protected") | "    enforcement=" + .enforcement + " bypass_actors=" + (.bypass_actors|length|tostring) + " rules=" + ([.rules[].type]|join(","))'
done

echo
echo "Done. Robot-side check (as PatricksRobot, expected: cannot bypass):"
echo "  gh api repos/${OWNER}/nfl-stats/rulesets   # read-only view if permitted"
