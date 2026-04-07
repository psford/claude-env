#!/usr/bin/env python3
"""
Claude Code PreToolUse hook: JS coordinate truthiness guard.

Fires on git commit. Blocks when staged wwwroot/js/*.js files use
truthiness checks on coordinate variables, which treat 0 as falsy and
silently fall back to wrong values.

Detected patterns:
  lat || fallback       (OR-fallback — 0 is falsy)
  lat ? x : y           (ternary — not ?? which is correct)
  if (lat)              (truthiness guard)
  if (!lng)             (negated truthiness guard)

Coordinate variable names checked:
  lat, lng, lon, longitude, latitude,
  centroidLat, centroidLng,
  minLat, maxLat, minLng, maxLng,
  south, north, east, west

Skip lines annotated with // COORD-TRUTHY-OK:

The correct operator is ?? (nullish coalescing), which only
falls back on null/undefined — not on 0.

Exit codes:
  0 = allow commit
  2 = block commit (with stderr message)
"""

import json
import re
import subprocess
import sys


SOURCE_JS_PATTERN = re.compile(r'wwwroot/js/[^/]+\.js$', re.IGNORECASE)

SKIP_ANNOTATION = re.compile(r'//\s*COORD-TRUTHY-OK\s*:', re.IGNORECASE)

COORD_NAMES = [
    "lat", "lng", "lon", "longitude", "latitude",
    "centroidLat", "centroidLng",
    "minLat", "maxLat", "minLng", "maxLng",
    "south", "north", "east", "west",
]

# Build a single alternation pattern for coordinate names (word-boundary aware)
_COORD_ALT = "(?:" + "|".join(re.escape(n) for n in COORD_NAMES) + ")"

# OR-fallback: coord || something
# e.g. lat || 0  /  lng || defaultLng  /  (data.lat || 0)
OR_FALLBACK = re.compile(
    r'\b' + _COORD_ALT + r'\b\s*\|\|',
    re.IGNORECASE
)

# Ternary: coord ? x : y  (but NOT coord ?? x)
# Match coord followed by ? but NOT ??
TERNARY = re.compile(
    r'\b' + _COORD_ALT + r'\b\s*\?(?!\?)',
    re.IGNORECASE
)

# if (coord) — plain truthiness check
IF_TRUTHY = re.compile(
    r'\bif\s*\(\s*' + _COORD_ALT + r'\b',
    re.IGNORECASE
)

# if (!coord) — negated truthiness check
IF_FALSY = re.compile(
    r'\bif\s*\(\s*!' + _COORD_ALT + r'\b',
    re.IGNORECASE
)

CHECKS = [
    (OR_FALLBACK, "OR-fallback (|| treats 0 as falsy)"),
    (TERNARY,     "ternary on coordinate (treats 0 as falsy)"),
    (IF_TRUTHY,   "truthiness guard (if(coord) — 0 is falsy)"),
    (IF_FALSY,    "negated truthiness guard (if(!coord) — 0 is falsy)"),
]


def run_git(*args, timeout=10):
    try:
        result = subprocess.run(
            ["git"] + list(args), capture_output=True, text=True, timeout=timeout
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def get_staged_js_files():
    output = run_git("diff", "--cached", "--name-only")
    return [
        f.strip()
        for f in output.splitlines()
        if f.strip() and SOURCE_JS_PATTERN.search(f.strip())
    ]


def read_staged_content(filepath):
    return run_git("show", f":{filepath}")


def check_file(fpath, content):
    """Return list of violation dicts for this file."""
    violations = []
    for lineno, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.rstrip()

        stripped = line.lstrip()
        if not stripped or stripped.startswith("//"):
            continue

        if SKIP_ANNOTATION.search(line):
            continue

        for pattern, description in CHECKS:
            m = pattern.search(line)
            if m:
                # Extract the matched coordinate name for clarity
                coord = m.group(0).strip()
                violations.append({
                    "file": fpath,
                    "line": lineno,
                    "description": description,
                    "coord_match": coord,
                    "text": stripped[:120],
                })
                break  # one violation per line is enough

    return violations


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name != "Bash":
        return 0

    command = tool_input.get("command", "")
    if not re.search(r'\bgit\b.*\bcommit\b', command, re.IGNORECASE):
        return 0

    staged_js = get_staged_js_files()
    if not staged_js:
        return 0

    all_violations = []
    for fpath in staged_js:
        content = read_staged_content(fpath)
        if not content:
            continue
        all_violations.extend(check_file(fpath, content))

    if not all_violations:
        return 0

    lines = [
        "",
        "=" * 70,
        "BLOCKED: Coordinate truthiness check — 0 treated as falsy",
        "=" * 70,
        "",
        "Coordinates can legitimately be 0 (e.g. lat=0 is the equator,",
        "lng=0 is the prime meridian). Truthiness checks silently fall back",
        "to a wrong value when the coordinate is exactly 0.",
        "",
        "Use ?? (nullish coalescing) instead — it only falls back on",
        "null or undefined, not on 0.",
        "",
        "  WRONG:   lat || defaultLat",
        "  CORRECT: lat ?? defaultLat",
        "",
        "  WRONG:   if (lat) { ... }",
        "  CORRECT: if (lat !== null && lat !== undefined) { ... }",
        "           if (lat != null) { ... }   // null-loose covers both",
        "",
    ]

    for v in all_violations:
        lines.append(f"  {v['file']}:{v['line']}  [{v['description']}]")
        lines.append(f"    Code: {v['text']}")
        lines.append("")

    lines += [
        "To suppress a confirmed false positive, annotate the line:",
        "  lat || 0 // COORD-TRUTHY-OK: lat is pre-validated non-null non-zero",
        "=" * 70,
    ]

    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
