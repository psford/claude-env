"""CE-2.96: the fixture vacuity sweep's report is the deliverable this test
reads, not a sweep this test runs itself.

Every hook fixture directory under .claude/hooks/tests/ was swept in a
scratch copy with its hook replaced by a no-op (reads stdin, exits 0, prints
nothing), and each BLOCK or FIRES fixture that still passed under that
no-op was recorded in docs/reviews/2026-09-27-fixture-vacuity-sweep.md. A
PASS fixture passing under a no-op is expected and excluded by construction
(CE-2.96 replaces CE-2.24, whose sweep tried to exclude PASS fixtures from a
uniform no-op result and could not).

This file is the python-level test the ticket's acceptance criteria name.
It asserts properties of the committed report; it does not re-run the sweep.

Run: python3 tests/test_fixture_vacuity_report.py
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "docs", "reviews", "2026-09-27-fixture-vacuity-sweep.md")
FIXTURES_DIR = os.path.join(ROOT, ".claude", "hooks", "tests")

# The known discriminating fixtures from CE-2.24's blocked run: a FIRES
# fixture that fails under a no-op (so must not be listed as surviving),
# and two PASS fixtures (so must not be listed at all, per AC2).
KNOWN_DISCRIMINATING = [
    ("retro_area_overlap_guard", "01"),
    ("shadow_command_guard", "22"),
    ("shadow_command_guard", "23"),
]


def _fixture_directories():
    """Every subdirectory of .claude/hooks/tests/ that holds *.md fixtures."""
    dirs = []
    for name in sorted(os.listdir(FIXTURES_DIR)):
        path = os.path.join(FIXTURES_DIR, name)
        if not os.path.isdir(path):
            continue
        if any(f.endswith(".md") for f in os.listdir(path) if f[0].isdigit()):
            dirs.append(name)
    return dirs


def _report_text():
    with open(REPORT, encoding="utf-8") as fh:
        return fh.read()


# Matches a fixture reference anywhere in the report, e.g.
# "shadow_command_guard/22-...BLOCK.md" or "22-....FIRES.md" under a
# "### shadow_command_guard" heading. We collect (heading, filename) pairs.
HEADING_RE = re.compile(r"^#+\s+`?([a-z0-9_]+)`?", re.MULTILINE)
FIXTURE_FILENAME_RE = re.compile(
    r"([0-9]+-[A-Za-z0-9_.\-]+\.(?:PASS|BLOCK|FIRES|SILENT)\.md)"
)


def _fixtures_listed_as_surviving(text):
    """(directory, filename) pairs the report lists as surviving, one per
    line under each directory's section -- found by scanning line by line
    and tracking the most recent hook-directory heading seen."""
    current_dir = None
    known_dirs = set(_fixture_directories())
    results = []
    for line in text.splitlines():
        heading = HEADING_RE.match(line)
        if heading and heading.group(1) in known_dirs:
            current_dir = heading.group(1)
            continue
        for fname in FIXTURE_FILENAME_RE.findall(line):
            if current_dir is not None:
                results.append((current_dir, fname))
    return results


class TestTheVacuityReport(unittest.TestCase):
    def test_every_fixture_directory_is_covered(self):
        self.assertTrue(
            os.path.isfile(REPORT),
            "docs/reviews/2026-09-27-fixture-vacuity-sweep.md does not exist",
        )
        text = _report_text()
        missing = [d for d in _fixture_directories() if d not in text]
        self.assertEqual(missing, [], "directories missing from the report: %s" % missing)

    def test_only_block_or_fires_fixtures_are_listed(self):
        text = _report_text()
        surviving = _fixtures_listed_as_surviving(text)
        non_block_fires = [
            (d, f) for (d, f) in surviving if not re.search(r"\.(BLOCK|FIRES)\.md$", f)
        ]
        self.assertEqual(
            non_block_fires,
            [],
            "fixtures listed as surviving that are not BLOCK or FIRES: %s" % non_block_fires,
        )

    def test_the_known_discriminating_fixtures_are_not_listed(self):
        text = _report_text()
        surviving = _fixtures_listed_as_surviving(text)
        for directory, number in KNOWN_DISCRIMINATING:
            hits = [
                (d, f)
                for (d, f) in surviving
                if d == directory and f.startswith(number + "-")
            ]
            self.assertEqual(
                hits,
                [],
                "%s fixture %s is listed as surviving but must not be" % (directory, number),
            )


if __name__ == "__main__":
    unittest.main()
