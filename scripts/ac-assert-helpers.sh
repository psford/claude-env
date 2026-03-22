#!/usr/bin/env bash
# ac-assert-helpers.sh — Behavioral assertion library for AC verification scripts.
#
# Usage: source scripts/ac-assert-helpers.sh
#
# Each assertion prints either:
#   PASS:<label>:<detail>
#   FAIL:<label>:<detail>
#
# The calling script is responsible for collecting results and reporting a summary.
# This library does NOT call exit — callers handle pass/fail accounting.

# ── HTTP status assertion ─────────────────────────────────────────────────────
#
# assert_http_status "label" "url" "expected_status"
#
# Sends a GET request to url and checks that the HTTP status code matches.
# Uses curl with a 10-second timeout. Returns PASS or FAIL.
assert_http_status() {
  local label="$1"
  local url="$2"
  local expected_status="$3"

  if ! command -v curl &>/dev/null; then
    echo "FAIL:${label}:curl not installed"
    return
  fi

  local actual_status
  actual_status=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")

  if [ "$actual_status" = "$expected_status" ]; then
    echo "PASS:${label}:HTTP ${actual_status} from ${url}"
  else
    echo "FAIL:${label}:expected HTTP ${expected_status}, got ${actual_status} from ${url}"
  fi
}

# ── HTTP body pattern assertion ───────────────────────────────────────────────
#
# assert_http_body_contains "label" "url" "pattern"
#
# Sends a GET request and checks that the response body contains pattern (grep -q).
assert_http_body_contains() {
  local label="$1"
  local url="$2"
  local pattern="$3"

  if ! command -v curl &>/dev/null; then
    echo "FAIL:${label}:curl not installed"
    return
  fi

  local body
  body=$(curl -sS --max-time 10 "$url" 2>/dev/null || true)

  if echo "$body" | grep -q "$pattern" 2>/dev/null; then
    echo "PASS:${label}:found pattern '${pattern}' in response from ${url}"
  else
    echo "FAIL:${label}:pattern '${pattern}' not found in response from ${url}"
  fi
}

# ── Git path prefix assertion ─────────────────────────────────────────────────
#
# assert_git_no_path_prefix "label" "repo_dir" "forbidden_prefix"
#
# Checks that git log --name-only in repo_dir contains no file paths starting
# with forbidden_prefix. A pass means filter-repo successfully removed those paths.
assert_git_no_path_prefix() {
  local label="$1"
  local repo_dir="$2"
  local forbidden_prefix="$3"

  if [ ! -d "$repo_dir/.git" ]; then
    echo "FAIL:${label}:${repo_dir} is not a git repository"
    return
  fi

  local hits
  hits=$(git -C "$repo_dir" log --name-only --pretty=format: 2>/dev/null \
    | grep -c "^${forbidden_prefix}" 2>/dev/null || echo "0")

  if [ "$hits" -eq 0 ]; then
    echo "PASS:${label}:no paths with prefix '${forbidden_prefix}' in git log"
  else
    echo "FAIL:${label}:found ${hits} path(s) with prefix '${forbidden_prefix}' in git log"
  fi
}

# ── JSON field assertion ──────────────────────────────────────────────────────
#
# assert_json_field "label" "file" "key" "expected"
#
# Reads file as JSON and checks that the top-level key equals expected value.
# Requires python3 (or jq if available).
assert_json_field() {
  local label="$1"
  local file="$2"
  local key="$3"
  local expected="$4"

  if [ ! -f "$file" ]; then
    echo "FAIL:${label}:file not found: ${file}"
    return
  fi

  local actual
  if command -v jq &>/dev/null; then
    actual=$(jq -r --arg k "$key" '.[$k] // empty' "$file" 2>/dev/null || echo "")
  elif command -v python3 &>/dev/null; then
    actual=$(python3 -c "
import sys, json
try:
    with open('$file') as f:
        data = json.load(f)
    val = data.get('$key', '')
    print('' if val is None else str(val))
except Exception as e:
    print('')
    sys.exit(0)
" 2>/dev/null || echo "")
  else
    echo "FAIL:${label}:neither jq nor python3 available to parse JSON"
    return
  fi

  if [ "$actual" = "$expected" ]; then
    echo "PASS:${label}:${key}=${actual}"
  else
    echo "FAIL:${label}:${key}: expected '${expected}', got '${actual}'"
  fi
}

# ── File contains pattern (with minimum count) assertion ─────────────────────
#
# assert_file_contains_pattern "label" "file" "pattern" min_count
#
# Counts occurrences of pattern in file. Passes if count >= min_count.
assert_file_contains_pattern() {
  local label="$1"
  local file="$2"
  local pattern="$3"
  local min_count="${4:-1}"

  if [ ! -f "$file" ]; then
    echo "FAIL:${label}:file not found: ${file}"
    return
  fi

  local count
  count=$(grep -c "$pattern" "$file" 2>/dev/null || echo "0")

  if [ "$count" -ge "$min_count" ]; then
    echo "PASS:${label}:found ${count} occurrence(s) of '${pattern}' in ${file} (min ${min_count})"
  else
    echo "FAIL:${label}:found ${count} occurrence(s) of '${pattern}' in ${file}, need >= ${min_count}"
  fi
}

# ── File does not contain pattern assertion ───────────────────────────────────
#
# assert_file_does_not_contain "label" "file" "pattern"
#
# Passes if pattern is NOT found in file.
assert_file_does_not_contain() {
  local label="$1"
  local file="$2"
  local pattern="$3"

  if [ ! -f "$file" ]; then
    echo "FAIL:${label}:file not found: ${file}"
    return
  fi

  if grep -q "$pattern" "$file" 2>/dev/null; then
    local line
    line=$(grep -n "$pattern" "$file" 2>/dev/null | head -1)
    echo "FAIL:${label}:forbidden pattern '${pattern}' found in ${file}: ${line}"
  else
    echo "PASS:${label}:pattern '${pattern}' not found in ${file}"
  fi
}

# ── GitHub API field assertion ────────────────────────────────────────────────
#
# assert_gh_api_field "label" "api_path" "jq_expr"
#
# Calls `gh api api_path` and evaluates jq_expr against the JSON response.
# Passes if jq_expr returns a non-empty, non-null, non-false value.
# Requires gh CLI and jq.
assert_gh_api_field() {
  local label="$1"
  local api_path="$2"
  local jq_expr="$3"

  if ! command -v gh &>/dev/null; then
    echo "FAIL:${label}:gh CLI not installed"
    return
  fi

  if ! command -v jq &>/dev/null; then
    echo "FAIL:${label}:jq not installed"
    return
  fi

  local response
  if ! response=$(gh api "$api_path" 2>/dev/null); then
    echo "FAIL:${label}:gh api ${api_path} failed (auth or network error)"
    return
  fi

  local value
  value=$(echo "$response" | jq -r "$jq_expr" 2>/dev/null || echo "")

  if [ -z "$value" ] || [ "$value" = "null" ] || [ "$value" = "false" ]; then
    echo "FAIL:${label}:${jq_expr} returned '${value}' from ${api_path}"
  else
    echo "PASS:${label}:${jq_expr} = ${value}"
  fi
}
