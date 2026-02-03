#!/usr/bin/env python3
"""
Pre-commit hook: BLOCK commits with unsanitized log parameters in C# code.

All structured log parameters that could contain user input MUST be wrapped
in LogSanitizer.Sanitize(). This prevents log injection/forging attacks
(CWE-117) where malicious input injects fake log entries via control chars.

This hook BLOCKS the commit (exit 1) if violations are found. No exceptions.

Safe patterns that are NOT flagged:
- Numeric values: .ElapsedMilliseconds, .Count, .Length, .TotalRecords, etc.
- String literals: "hardcoded"
- Enum/type names: provider.ProviderName, .Source, .Status
- Already sanitized: LogSanitizer.Sanitize(value)
- Structured logging with no string params: Log.Information("Starting server")
"""

import re
import subprocess
import sys


# Matches log calls: _logger?.Log*, Log.Information, Log.Warning, etc.
LOG_PATTERN = re.compile(
    r'(?:_logger\?\.|Log\.)'
    r'(?:LogDebug|LogInformation|LogWarning|LogError|LogCritical|LogTrace|'
    r'Debug|Information|Warning|Error|Fatal|Verbose)'
    r'\s*\('
)

# Matches structured log placeholders like {Company}, {Ticker}, {Title}
PLACEHOLDER_PATTERN = re.compile(r'\{(\w+)\}')

# Parameters that are inherently safe (numeric, internal, or non-user-input).
# These don't need LogSanitizer.Sanitize() wrapping.
SAFE_PARAM_PATTERNS = [
    r'LogSanitizer\.Sanitize\(',       # Already sanitized
    r'\.\w*(?:Count|Length|Id|Alias)\b', # Numeric properties
    r'\.Elapsed\w*',                     # Stopwatch values
    r'\.Total\w*',                       # Aggregate counts
    r'\.TotalMilliseconds',              # TimeSpan
    r'\.TotalSeconds',                   # TimeSpan
    r'nameof\(',                         # nameof() expressions
    r'typeof\(',                         # typeof() expressions
    r'\bex\b',                           # Exception variable
    r'\"[^"]*\"',                        # String literals
    r'\b\d+\b',                          # Numeric literals
    r'\.ProviderName\b',                 # Internal provider names
    r'\.Name\b',                         # Internal names (not user input)
    r'\.Status\b',                       # Enum-like status values
    r'\.GetType\(\)',                     # Type names
    r'DateTime\.',                        # DateTime values
    r'TimeSpan\.',                        # TimeSpan values
    r'Guid\.',                            # Guid values
    r'\.ToString\("',                     # Formatted ToString with format string
    r'Environment\.',                     # Environment variables
    r'Assembly\.',                        # Assembly info
    r'\.Version\b',                       # Version info
    r'\.Key\b',                           # Dictionary keys (internal)
    r'\.Value\b',                         # Dictionary values (context-dependent)
    r'delay\.TotalMilliseconds',          # Rate limiter delay
]

SAFE_PARAM_RE = re.compile('|'.join(SAFE_PARAM_PATTERNS))


def get_staged_cs_diffs():
    """Get added/modified lines from staged C# files."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--unified=0', '--diff-filter=ACMR',
         '--', '*.cs'],
        capture_output=True, text=True
    )
    return result.stdout


def parse_added_lines(diff_output):
    """Parse diff output to get (filename, line_number, line_content) for added lines."""
    lines = []
    current_file = None
    current_line = 0

    for line in diff_output.split('\n'):
        if line.startswith('+++ b/'):
            current_file = line[6:]
        elif line.startswith('@@'):
            # Parse @@ -old,count +new,count @@
            match = re.search(r'\+(\d+)', line)
            if match:
                current_line = int(match.group(1)) - 1  # Will be incremented
        elif line.startswith('+') and not line.startswith('+++'):
            current_line += 1
            content = line[1:]  # Strip leading +
            if current_file:
                lines.append((current_file, current_line, content))
        elif not line.startswith('-'):
            current_line += 1

    return lines


def extract_params_after_format_string(line, log_match_end):
    """Extract the parameter portion after the format string in a log call."""
    # Find the format string (first quoted string after the log method)
    rest = line[log_match_end:]

    # Handle exception parameter: Log.Warning(ex, "message", params)
    # Skip past 'ex,' or similar exception variable
    rest = rest.strip()

    # Find the format string by looking for the first quoted string
    in_string = False
    escape_next = False
    paren_depth = 1  # We're already inside the opening paren
    format_end = -1
    i = 0

    while i < len(rest):
        c = rest[i]
        if escape_next:
            escape_next = False
            i += 1
            continue

        if c == '\\':
            escape_next = True
            i += 1
            continue

        if c == '"' and not in_string:
            # Found start of format string, now find end
            in_string = True
            i += 1
            continue

        if c == '"' and in_string:
            # Check for verbatim string @" or interpolated $"
            # For simplicity, just find closing quote
            in_string = False
            format_end = i
            i += 1
            continue

        if not in_string:
            if c == '(':
                paren_depth += 1
            elif c == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    break

        i += 1

    if format_end < 0:
        return ""

    # Everything after the format string closing quote to the closing paren
    params_section = rest[format_end + 1:i].strip()
    if params_section.startswith(','):
        params_section = params_section[1:].strip()

    return params_section


def check_params_sanitized(params_str):
    """Check if all parameters in the string are either safe or sanitized.
    Returns list of suspicious parameter expressions."""
    if not params_str.strip():
        return []

    # Split by comma, respecting parentheses depth
    params = []
    current = []
    depth = 0
    for c in params_str:
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        elif c == ',' and depth == 0:
            params.append(''.join(current).strip())
            current = []
            continue
        current.append(c)
    if current:
        params.append(''.join(current).strip())

    suspicious = []
    for param in params:
        param = param.strip()
        if not param:
            continue

        # Check if this parameter matches any safe pattern
        if SAFE_PARAM_RE.search(param):
            continue

        # If it's a simple variable name or property access that could be
        # user input, flag it
        suspicious.append(param)

    return suspicious


def main():
    diff_output = get_staged_cs_diffs()
    if not diff_output:
        return 0

    added_lines = parse_added_lines(diff_output)
    violations = []

    for filepath, line_num, content in added_lines:
        # Skip test project directories (not files that happen to contain "test")
        if '/tests/' in filepath.lower() or '\\tests\\' in filepath.lower() \
                or '.tests/' in filepath.lower() or '.tests\\' in filepath.lower():
            continue

        # Skip comment lines
        stripped = content.strip()
        if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('///'):
            continue

        # Find log calls in this line
        for match in LOG_PATTERN.finditer(content):
            params_str = extract_params_after_format_string(content, match.end())
            suspicious = check_params_sanitized(params_str)

            if suspicious:
                violations.append({
                    'file': filepath,
                    'line': line_num,
                    'params': suspicious,
                    'content': stripped,
                })

    if violations:
        print("\n" + "=" * 70)
        print("BLOCKED: Unsanitized log parameters detected (CWE-117)")
        print("=" * 70)
        print("\nAll user-facing string parameters in log calls MUST be wrapped")
        print("in LogSanitizer.Sanitize() to prevent log injection attacks.\n")

        for v in violations:
            print(f"  {v['file']}:{v['line']}")
            print(f"    {v['content'][:120]}")
            print(f"    Unsanitized: {', '.join(v['params'])}")
            print()

        print("Fix: Wrap each parameter with LogSanitizer.Sanitize(value)")
        print("     using StockAnalyzer.Core.Helpers;")
        print("=" * 70 + "\n")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
