#!/usr/bin/env python3
"""Lint a port table for two entries claiming the same local port (CE-2.84).

Parses the "Port" column of a markdown table -- a bare number ("8787") or
a hyphenated range ("8790-8799") -- and exits 1 if any two entries claim
an overlapping port. Exits 0, with no output, when every row is exclusive.

Usage:
    python3 helpers/port_lint.py docs/ports.md
"""

import re
import sys
from pathlib import Path

ROW_RE = re.compile(r"^\|\s*(\d+)(?:\s*-\s*(\d+))?\s*\|")


def parse_ports(text):
    """Return a list of (start, end, raw_line) for each data row's Port
    cell. A bare port N becomes (N, N, line). Rows whose first cell isn't
    all digits -- the header and the '---' separator -- are skipped."""
    entries = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        entries.append((start, end, line.strip()))
    return entries


def find_collisions(entries):
    """Return a list of (entry_a, entry_b) pairs whose [start, end] ranges
    overlap, comparing every pair once."""
    collisions = []
    for i in range(len(entries)):
        a_start, a_end, _ = entries[i]
        for j in range(i + 1, len(entries)):
            b_start, b_end, _ = entries[j]
            if a_start <= b_end and b_start <= a_end:
                collisions.append((entries[i], entries[j]))
    return collisions


def main(argv):
    if len(argv) != 2:
        print("usage: port_lint.py <path-to-ports-table.md>", file=sys.stderr)
        return 2
    text = Path(argv[1]).read_text()
    entries = parse_ports(text)
    collisions = find_collisions(entries)
    if collisions:
        for a, b in collisions:
            print(
                f"port_lint: two entries claim port {max(a[0], b[0])}:\n"
                f"  {a[2]}\n  {b[2]}",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
