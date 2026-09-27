"""Tests for docs/reviews/2026-09-27-hook-wiring-inventory.md (CE-2.21).

Checks that the committed hook-wiring report accounts for every hook file in
.claude/hooks/*.py, that every table row names its wiring (or says it has
none), and that the six incident hooks are each called out by name outside
the table.
"""
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = REPO_ROOT / "docs" / "reviews" / "2026-09-27-hook-wiring-inventory.md"
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"

INCIDENT_HOOKS = [
    "js_test_theater_guard",
    "ef_migration_guard",
    "api_integration_test_gate",
    "cherry_pick_guard",
    "stale_path_guard",
    "workaround_guard",
]


def _hook_basenames():
    return sorted(p.stem for p in HOOKS_DIR.glob("*.py"))


def _report_text():
    return REPORT_PATH.read_text()


def _table_rows(text):
    """Return the markdown table lines (rows starting with '|') that are not
    the header or separator row."""
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r"^\|[\s:|-]+\|$", stripped):
            continue
        rows.append(stripped)
    return rows


class TestTheHookWiringReport(unittest.TestCase):
    def test_every_hook_file_has_a_row(self):
        self.assertTrue(
            REPORT_PATH.exists(),
            f"report not found at {REPORT_PATH}",
        )
        text = _report_text()
        rows = _table_rows(text)
        hooks = _hook_basenames()
        self.assertTrue(hooks, "expected at least one .claude/hooks/*.py file")
        missing = []
        for hook in hooks:
            if not any(hook in row for row in rows):
                missing.append(hook)
        self.assertEqual(
            missing,
            [],
            f"hooks missing a table row in {REPORT_PATH}: {missing}",
        )

    def test_each_row_names_its_wiring(self):
        text = _report_text()
        rows = _table_rows(text)
        # Skip the header row itself (contains "Hook" as a column title).
        data_rows = [r for r in rows if not re.search(r"\bHook\b", r)]
        self.assertTrue(data_rows, "expected data rows in the report table")
        for row in data_rows:
            names_nowhere = "wired nowhere" in row
            names_settings = bool(
                re.search(r"settings(\.local)?\.json|hooks\.json", row)
            )
            self.assertTrue(
                names_nowhere or names_settings,
                f"row does not name its wiring or say 'wired nowhere': {row}",
            )

    def test_the_incident_hooks_are_accounted_for(self):
        text = _report_text()
        # "Outside the table" means somewhere other than the table rows.
        rows = _table_rows(text)
        non_table_text = "\n".join(
            line for line in text.splitlines() if line.strip() not in rows
        )
        missing = [h for h in INCIDENT_HOOKS if h not in non_table_text]
        self.assertEqual(
            missing,
            [],
            f"incident hooks not accounted for outside the table: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
