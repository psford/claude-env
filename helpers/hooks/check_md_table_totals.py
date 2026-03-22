#!/usr/bin/env python3
"""
Pre-commit hook: Validate arithmetic in markdown table "Total" rows.

Mitigation #6 from retrospective. Detects rows labeled "Total" in markdown
tables and verifies the numeric columns sum correctly.

Exit 0 if all totals match (or no totals found).
Exit 1 if any mismatch is detected.
"""

import subprocess
import sys
import re


def get_staged_md_files():
    """Return list of staged .md files (added, copied, or modified)."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "--", "*.md"],
        capture_output=True, text=True
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def parse_cell(text):
    """Strip whitespace from a table cell."""
    return text.strip()


def is_separator_row(cells):
    """Check if a row is a markdown table separator (e.g., | --- | :---: |)."""
    return all(re.match(r'^[\s\-:]*$', cell) and '-' in cell for cell in cells)


def parse_numeric(text):
    """Try to parse a cell as a number. Returns (value, True) or (None, False).

    Handles: commas (1,234), percentages (95%), negative numbers, decimals.
    """
    s = text.strip()
    if not s:
        return None, False

    # Remove percentage sign
    s = s.rstrip('%').strip()

    # Remove commas
    s = s.replace(',', '')

    try:
        return int(s), True
    except ValueError:
        pass
    try:
        return float(s), True
    except ValueError:
        return None, False


def split_row(line):
    """Split a markdown table row into cells, stripping the outer pipes."""
    # Remove leading/trailing pipe and split
    stripped = line.strip()
    if stripped.startswith('|'):
        stripped = stripped[1:]
    if stripped.endswith('|'):
        stripped = stripped[:-1]
    return [parse_cell(c) for c in stripped.split('|')]


def extract_tables(lines):
    """Extract markdown tables from file lines.

    Returns a list of tables, where each table is a dict:
        {
            'start_line': int (1-based),
            'header': [str, ...],
            'data_rows': [([str, ...], line_number), ...],
            'total_row': ([str, ...], line_number) or None,
        }
    """
    tables = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Look for the start of a table: a pipe-delimited line followed by a separator
        if line.startswith('|') and i + 1 < len(lines):
            header_cells = split_row(line)
            next_line = lines[i + 1].strip()
            if next_line.startswith('|'):
                sep_cells = split_row(next_line)
                if is_separator_row(sep_cells):
                    # We have a table header + separator
                    table = {
                        'start_line': i + 1,  # 1-based
                        'header': header_cells,
                        'data_rows': [],
                        'total_row': None,
                    }
                    j = i + 2  # first data row
                    while j < len(lines):
                        row_line = lines[j].strip()
                        if not row_line.startswith('|'):
                            break
                        row_cells = split_row(row_line)
                        # Check if this is a Total row
                        if row_cells and row_cells[0].lower().strip() == 'total':
                            table['total_row'] = (row_cells, j + 1)
                            j += 1
                            break
                        # Skip additional separator rows within a table
                        if not is_separator_row(row_cells):
                            table['data_rows'].append((row_cells, j + 1))
                        j += 1
                    tables.append(table)
                    i = j
                    continue
        i += 1
    return tables


def check_table(table, filepath, errors):
    """Validate the Total row arithmetic for a single table."""
    total_row, total_line = table['total_row']
    data_rows = table['data_rows']

    if not data_rows:
        return

    num_cols = len(total_row)

    for col_idx in range(1, num_cols):  # Skip first column (label column)
        # Check if the total cell is numeric
        total_text = total_row[col_idx] if col_idx < len(total_row) else ''
        total_val, total_is_numeric = parse_numeric(total_text)
        if not total_is_numeric:
            continue

        # Check if this column is consistently numeric in data rows
        col_values = []
        all_numeric = True
        for row_cells, _ in data_rows:
            cell_text = row_cells[col_idx] if col_idx < len(row_cells) else ''
            val, is_num = parse_numeric(cell_text)
            if cell_text.strip() == '':
                # Treat empty cells as 0
                col_values.append(0)
            elif is_num:
                col_values.append(val)
            else:
                all_numeric = False
                break

        if not all_numeric:
            continue

        expected = sum(col_values)

        # Compare with tolerance for floating point
        if isinstance(expected, float) or isinstance(total_val, float):
            if abs(expected - total_val) > 0.01:
                col_name = table['header'][col_idx] if col_idx < len(table['header']) else f"column {col_idx}"
                errors.append(
                    f"  {filepath} (table at line {table['start_line']}, "
                    f"column \"{col_name}\"): "
                    f"expected {expected}, found {total_val}"
                )
        else:
            if expected != total_val:
                col_name = table['header'][col_idx] if col_idx < len(table['header']) else f"column {col_idx}"
                errors.append(
                    f"  {filepath} (table at line {table['start_line']}, "
                    f"column \"{col_name}\"): "
                    f"expected {expected}, found {total_val}"
                )


def check_file(filepath, errors):
    """Check all tables in a single markdown file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return

    tables = extract_tables(lines)
    for table in tables:
        if table['total_row'] is not None:
            check_table(table, filepath, errors)


def main():
    md_files = get_staged_md_files()
    if not md_files:
        sys.exit(0)

    errors = []
    for filepath in md_files:
        check_file(filepath, errors)

    if errors:
        print("Markdown table total mismatches found:")
        for error in errors:
            print(error)
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
