#!/usr/bin/env bash
# deploy-gate.sh — shared pre-deploy structural gate.
#
# SOURCE this from a repo's own preflight script after setting the config
# vars below; call `deploy_gate_check` to run it. Exits non-zero (via the
# caller's `set -e`) on any failure — this is a hard block, not advisory.
#
# Required vars (set before sourcing):
#   DEPLOY_GATE_BRANCH        - branch that must be checked out (e.g. "main")
#   DEPLOY_GATE_FILE          - path to the stamped gate file (e.g. ".deploy-gate")
#   DEPLOY_GATE_MAX_AGE_HOURS - reject a stamp older than this (default 24)
#   DEPLOY_GATE_VISUAL_PATHS  - grep -E pattern; if the diff since the last
#                                successful deploy touches a matching path,
#                                require VISUAL_REVIEWED=1
#   DEPLOY_GATE_LAST_SHA_FILE - path to the "last successfully deployed sha"
#                                marker (e.g. ".last-deploy-sha"), gitignored
#
# Escape hatch (per-check, logged — no blanket bypass):
#   DEPLOY_GATE_E2E_OVERRIDE=1   skips the e2e-freshness check only.
#   Every use is appended to .deploy-gate-bypass.log (gitignored) with a
#   timestamp + whoami, so it's visible in `git status`/local history even
#   though it isn't committed.

deploy_gate_log_bypass() {
  echo "$(date -Iseconds) $(whoami) bypass=$1 sha=$(git rev-parse HEAD 2>/dev/null)" \
    >> .deploy-gate-bypass.log
}

deploy_gate_check() {
  local errors=0

  # 1. Correct branch.
  local branch; branch="$(git rev-parse --abbrev-ref HEAD)"
  if [ "$branch" != "$DEPLOY_GATE_BRANCH" ]; then
    echo "[deploy-gate] BLOCKED: on branch '$branch', deploys must run from '$DEPLOY_GATE_BRANCH'." >&2
    errors=1
  fi

  # 2. Clean tree.
  if [ -n "$(git status --porcelain)" ]; then
    echo "[deploy-gate] BLOCKED: working tree is not clean. Commit or stash before deploying." >&2
    git status --porcelain >&2
    errors=1
  fi

  # 3. HEAD == origin/<branch>. Fail CLOSED if we can't verify (no silent skip).
  if ! git fetch origin "$DEPLOY_GATE_BRANCH" --quiet 2>/dev/null; then
    echo "[deploy-gate] BLOCKED: could not fetch origin/$DEPLOY_GATE_BRANCH — cannot verify HEAD is what's on GitHub." >&2
    errors=1
  else
    local head_sha origin_sha
    head_sha="$(git rev-parse HEAD)"
    origin_sha="$(git rev-parse "origin/$DEPLOY_GATE_BRANCH")"
    if [ "$head_sha" != "$origin_sha" ]; then
      echo "[deploy-gate] BLOCKED: HEAD ($head_sha) != origin/$DEPLOY_GATE_BRANCH ($origin_sha)." >&2
      echo "  Push and let CI/PR review see this commit before deploying it." >&2
      errors=1
    fi
  fi

  # 4. e2e freshness: gate file must exist, match HEAD sha, and be recent.
  if [ "${DEPLOY_GATE_E2E_OVERRIDE:-0}" = "1" ]; then
    echo "[deploy-gate] WARNING: e2e-freshness check bypassed via DEPLOY_GATE_E2E_OVERRIDE=1 (logged)." >&2
    deploy_gate_log_bypass "e2e-freshness"
  elif [ ! -f "$DEPLOY_GATE_FILE" ]; then
    echo "[deploy-gate] BLOCKED: no $DEPLOY_GATE_FILE found. Run 'npm run gate:e2e' (full matrix) first." >&2
    errors=1
  else
    local gate_sha gate_ts now_epoch gate_epoch age_hours head_sha
    head_sha="$(git rev-parse HEAD)"
    # JSON.parse over readFileSync, NOT require(): the stamp file has no .json
    # extension, so Node's require() parses it as JS and throws on valid JSON
    # — which 2>/dev/null used to swallow into "", making the SHA check fail
    # against even a fresh, correct stamp (found by photo-portfolio dry-run,
    # 2026-07-09).
    gate_sha="$(node -e "console.log(JSON.parse(require('fs').readFileSync('$DEPLOY_GATE_FILE','utf8')).sha)" 2>/dev/null || echo "")"
    gate_ts="$(node -e "console.log(JSON.parse(require('fs').readFileSync('$DEPLOY_GATE_FILE','utf8')).timestamp)" 2>/dev/null || echo "")"
    if [ "$gate_sha" != "$head_sha" ]; then
      echo "[deploy-gate] BLOCKED: $DEPLOY_GATE_FILE is stamped for $gate_sha, HEAD is $head_sha." >&2
      echo "  The e2e matrix hasn't run against this exact commit. Run: npm run gate:e2e" >&2
      errors=1
    else
      gate_epoch="$(date -d "$gate_ts" +%s 2>/dev/null || echo 0)"
      now_epoch="$(date +%s)"
      age_hours=$(( (now_epoch - gate_epoch) / 3600 ))
      if [ "$age_hours" -gt "${DEPLOY_GATE_MAX_AGE_HOURS:-24}" ]; then
        echo "[deploy-gate] BLOCKED: $DEPLOY_GATE_FILE is $age_hours h old (limit ${DEPLOY_GATE_MAX_AGE_HOURS:-24}h). Re-run: npm run gate:e2e" >&2
        errors=1
      fi
    fi
  fi

  # 5. Visual-review ack for layout/style-affecting diffs since the last deploy.
  local last_sha=""
  [ -f "$DEPLOY_GATE_LAST_SHA_FILE" ] && last_sha="$(cat "$DEPLOY_GATE_LAST_SHA_FILE")"
  local visual_touched=""
  if [ -n "$last_sha" ] && git cat-file -e "$last_sha" 2>/dev/null; then
    visual_touched="$(git diff --name-only "$last_sha" HEAD | grep -E "$DEPLOY_GATE_VISUAL_PATHS" || true)"
  else
    visual_touched="(no prior deploy marker found — treating as visual change)"
  fi
  if [ -n "$visual_touched" ]; then
    if [ "${VISUAL_REVIEWED:-0}" != "1" ]; then
      echo "[deploy-gate] BLOCKED: this deploy touches layout/style paths and hasn't been visually ack'd:" >&2
      # shellcheck disable=SC2001  # multi-line prefix; parameter expansion can't do this cleanly
      echo "$visual_touched" | sed 's/^/  /' >&2
      echo "  Look at the change (npm run cf:dev, or a preview), then re-run with VISUAL_REVIEWED=1." >&2
      errors=1
    else
      echo "[deploy-gate] visual review acknowledged (VISUAL_REVIEWED=1)."
    fi
  fi

  return "$errors"
}

deploy_gate_record_success() {
  git rev-parse HEAD > "$DEPLOY_GATE_LAST_SHA_FILE"
}
