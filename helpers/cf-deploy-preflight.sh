#!/usr/bin/env bash
# Generic Cloudflare deploy preflight guard.
#
# Catches two classes of test-mode-leaks-into-production:
#
#   1. Shell-exported PUBLIC_* env vars — Astro (and any framework that
#      copies process.env.PUBLIC_* into the build) inlines shell env OVER
#      .env.production values. Any PUBLIC_* var left from a test run would
#      ship to workers.dev. Discovered dynamically (`compgen -v`), so a
#      future PUBLIC_* var added in a later phase is automatically covered.
#
#   2. Leftover ephemeral fixture in public/. Test suites (e.g.
#      `npm run test:smoke`) seed public/<fixture> from a fixtures
#      directory and rely on the file being gitignored. `astro build`
#      copies public/* into dist/* so a forgotten fixture ships to
#      production unless the deploy preflight catches it.
#
# Extracted from photo-portfolio (where it lived as
# scripts/cf-deploy-preflight.sh) and parameterized so any
# Cloudflare-deploying companion project can call it.
#
# Usage:
#   bash helpers/cf-deploy-preflight.sh [--public-prefix PUBLIC_] [--fixture public/manifest.json] ...
#
# Or invoke with env vars:
#   PREFIX=PUBLIC_ FIXTURES=public/manifest.json bash helpers/cf-deploy-preflight.sh
#
# Options:
#   --public-prefix <s>   Env-var prefix to scan for (default: PUBLIC_)
#   --fixture <path>      Ephemeral fixture file that must not exist at deploy
#                          (may be passed multiple times for multiple fixtures)
#
# Exit codes:
#   0   safe to deploy
#   1   one or more leaks detected (details on stderr)
#
# Per-project wrapping pattern:
#   scripts/cf-deploy-preflight.sh:
#     #!/usr/bin/env bash
#     bash /opt/claude-env/helpers/cf-deploy-preflight.sh \
#       --public-prefix PUBLIC_ \
#       --fixture public/manifest.json
#
# (Adjust the claude-env path for your bootstrap symlink.)

set -euo pipefail

PREFIX="${PREFIX:-PUBLIC_}"
FIXTURES=()
if [[ -n "${FIXTURES:-}" ]]; then
  # Allow comma-separated list via env: FIXTURES=a,b
  IFS=',' read -ra FIXTURES <<< "${FIXTURES}"
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --public-prefix)
      PREFIX="$2"
      shift 2
      ;;
    --fixture)
      FIXTURES+=("$2")
      shift 2
      ;;
    -h|--help)
      sed -n '2,40p' "$0"
      exit 0
      ;;
    *)
      echo "ERROR: unknown arg: $1" >&2
      echo "Usage: bash $0 [--public-prefix PUBLIC_] [--fixture path] ..." >&2
      exit 1
      ;;
  esac
done

errors=0

# --- Class 1: PREFIX* env-var leaks ---
leaked=()
while IFS= read -r var; do
  if [[ -n "${!var:-}" ]]; then
    leaked+=("$var=${!var}")
  fi
done < <(compgen -v | grep "^${PREFIX}" || true)

if [[ ${#leaked[@]} -gt 0 ]]; then
  echo "ERROR: ${PREFIX}* environment variables are exported in your shell." >&2
  echo "They would override .env.production during build and ship to the deployed worker:" >&2
  for entry in "${leaked[@]}"; do
    echo "  $entry" >&2
  done
  echo "" >&2
  echo "Unset them before deploying:" >&2
  for entry in "${leaked[@]}"; do
    echo "  unset ${entry%%=*}" >&2
  done
  echo "" >&2
  errors=1
fi

# --- Class 2: leftover ephemeral fixtures ---
for fixture in "${FIXTURES[@]}"; do
  if [[ -f "$fixture" ]]; then
    echo "ERROR: $fixture exists." >&2
    echo "  This is an ephemeral test fixture and is expected to be gitignored." >&2
    echo "  If you deploy with it present, the build will copy it into the bundle" >&2
    echo "  and the deployed worker will serve it instead of the production manifest." >&2
    echo "" >&2
    echo "  Remove it before deploying:" >&2
    echo "    rm $fixture" >&2
    echo "" >&2
    errors=1
  fi
done

if [[ "$errors" -eq 1 ]]; then
  exit 1
fi

echo "cf-deploy-preflight: shell env + fixtures clean — safe to bake .env.production into the bundle"
