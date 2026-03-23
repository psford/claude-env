#!/usr/bin/env bash
# Load .env file safely, handling values with semicolons, spaces, and special chars.
# Usage: source helpers/load-env.sh [path-to-env]
#
# Unlike `source .env`, this properly handles unquoted values containing
# semicolons (SQL connection strings), spaces, and special characters.

ENV_FILE="${1:-$(dirname "${BASH_SOURCE[0]}")/../.env}"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env file not found at $ENV_FILE" >&2
    return 1 2>/dev/null || exit 1
fi

while IFS= read -r line; do
    # Skip comments and blank lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$line" ]] && continue

    # Extract key=value, preserving everything after first = as the value
    key="${line%%=*}"
    value="${line#*=}"

    # Skip lines without =
    [[ "$key" == "$line" ]] && continue

    # Skip if key has spaces (not a valid env var)
    [[ "$key" =~ [[:space:]] ]] && continue

    export "$key=$value"
done < "$ENV_FILE"
