#!/usr/bin/env python3
"""Tests for helpers/port_lint.py (CE-2.84).

Run: python3 helpers/tests/test_port_lint.py
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HELPERS = Path(__file__).resolve().parent.parent
REPO = HELPERS.parent

NO_COLLISION = """| Port | Project | Where it's declared | What listens on it |
|------|---------|----------------------|---------------------|
| 8787 | claude-harness | dashboard/server.py | dashboard |
| 8788 | claude-harness | deploy-dashboard.sh | smoke |
| 8790-8799 | claude-harness | SKILL.md | preview range |
"""

COLLISION = """| Port | Project | Where it's declared | What listens on it |
|------|---------|----------------------|---------------------|
| 8787 | claude-harness | dashboard/server.py | dashboard |
| 8787 | wrangler | package.json | dev server |
"""


class TestPortLint(unittest.TestCase):
    def _run(self, path):
        return subprocess.run(
            [sys.executable, str(HELPERS / "port_lint.py"), str(path)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_the_shipped_table_has_no_collisions(self):
        result = self._run(REPO / "docs" / "ports.md")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_duplicate_port_is_refused(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False
        ) as f:
            f.write(COLLISION)
            temp_path = f.name
        result = self._run(temp_path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("8787", result.stderr)

    def test_a_table_with_no_overlap_passes(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False
        ) as f:
            f.write(NO_COLLISION)
            temp_path = f.name
        result = self._run(temp_path)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
