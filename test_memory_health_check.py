#!/usr/bin/env python3
"""
Unit tests for helpers/memory_health_check.py (CE-2.49)

Tests for:
- Dead [[link]] detection, and that a ticket-id-shaped [[link]] is excluded
- Dead cited-path detection, narrowed to backtick-quoted ~/ and /home/ paths
- load_memories skipping MEMORY.md and parsing frontmatter description + body
- The CLI's --quick, --memory-dir and exit-code contract end to end
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Import the module to test
helpers_dir = Path(__file__).parent / "helpers"
sys.path.insert(0, str(helpers_dir))
from memory_health_check import (  # noqa: E402
    find_dead_links,
    find_dead_paths,
    load_memories,
)


def write_memory(directory, key, desc, body):
    path = Path(directory) / f"{key}.md"
    path.write_text(
        f'---\nname: {key}\ndescription: "{desc}"\n---\n\n{body}\n',
        encoding="utf-8",
    )
    return path


class TestFindDeadLinks(unittest.TestCase):
    def test_link_to_missing_memory_is_dead(self):
        with tempfile.TemporaryDirectory() as d:
            write_memory(d, "feedback_alpha", "alpha", "See [[feedback_missing]].")
            write_memory(d, "feedback_beta", "beta", "No links here.")
            memories = load_memories(d)
            dead = find_dead_links(memories)
            self.assertEqual(len(dead), 1)
            self.assertEqual(dead[0]["memory"], "feedback_alpha")
            self.assertEqual(dead[0]["link"], "feedback_missing")

    def test_link_to_existing_memory_is_not_dead(self):
        with tempfile.TemporaryDirectory() as d:
            write_memory(d, "feedback_alpha", "alpha", "See [[feedback_beta]].")
            write_memory(d, "feedback_beta", "beta", "No links here.")
            memories = load_memories(d)
            self.assertEqual(find_dead_links(memories), [])

    def test_ticket_id_shaped_link_is_excluded(self):
        """A [[CE-2.49]]-shaped link was never meant to resolve to a memory
        file, so it must not be reported even though no such memory exists."""
        with tempfile.TemporaryDirectory() as d:
            write_memory(d, "feedback_alpha", "alpha", "Filed as [[CE-2.49]].")
            memories = load_memories(d)
            self.assertEqual(find_dead_links(memories), [])

    def test_hyphen_for_underscore_typo_is_still_reported(self):
        """A real key with a hyphen swapped in for an underscore does not
        match the ticket-id shape and must still be reported as dead."""
        with tempfile.TemporaryDirectory() as d:
            write_memory(d, "feedback_alpha", "alpha", "See [[feedback-beta]].")
            write_memory(d, "feedback_beta", "beta", "No links here.")
            memories = load_memories(d)
            dead = find_dead_links(memories)
            self.assertEqual(len(dead), 1)
            self.assertEqual(dead[0]["link"], "feedback-beta")


class TestFindDeadPaths(unittest.TestCase):
    def test_dead_home_rooted_path_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            write_memory(
                d, "feedback_alpha", "alpha",
                "See `/home/nobody/does-not-exist/file.py`.",
            )
            memories = load_memories(d)
            dead = find_dead_paths(memories)
            self.assertEqual(len(dead), 1)
            self.assertEqual(dead[0]["memory"], "feedback_alpha")
            self.assertEqual(dead[0]["path"], "/home/nobody/does-not-exist/file.py")

    def test_existing_home_rooted_path_is_not_dead(self):
        with tempfile.TemporaryDirectory() as d:
            write_memory(d, "feedback_alpha", "alpha", f"See `{__file__}`.")
            memories = load_memories(d)
            self.assertEqual(find_dead_paths(memories), [])

    def test_relative_path_is_not_checked_either_way(self):
        """Only ~/ and /home/-rooted backtick paths are resolved -- a bare
        relative citation like `foo.py` must not be reported as dead."""
        with tempfile.TemporaryDirectory() as d:
            write_memory(d, "feedback_alpha", "alpha", "See `nonexistent_file.py`.")
            memories = load_memories(d)
            self.assertEqual(find_dead_paths(memories), [])


class TestLoadMemories(unittest.TestCase):
    def test_memory_md_index_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            write_memory(d, "feedback_alpha", "alpha", "Body.")
            (Path(d) / "MEMORY.md").write_text("# Memory Index\n", encoding="utf-8")
            memories = load_memories(d)
            keys = {m["key"] for m in memories}
            self.assertEqual(keys, {"feedback_alpha"})

    def test_description_and_body_are_parsed(self):
        with tempfile.TemporaryDirectory() as d:
            write_memory(d, "feedback_alpha", "a short description", "The body text.")
            memories = load_memories(d)
            self.assertEqual(len(memories), 1)
            self.assertEqual(memories[0]["desc"], "a short description")
            self.assertIn("The body text.", memories[0]["body"])


class TestCli(unittest.TestCase):
    """End-to-end: the checker binary against a fixture directory."""

    def test_quick_mode_exits_nonzero_and_names_dead_link(self):
        with tempfile.TemporaryDirectory() as d:
            write_memory(d, "feedback_alpha", "alpha", "See [[feedback_missing]].")
            write_memory(d, "feedback_beta", "beta", "No links here.")
            result = subprocess.run(
                [
                    sys.executable,
                    str(helpers_dir / "memory_health_check.py"),
                    "--quick",
                    "--memory-dir",
                    d,
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("feedback_missing", result.stdout)
            self.assertIn("feedback_alpha", result.stdout)

    def test_quick_mode_exits_zero_when_clean(self):
        with tempfile.TemporaryDirectory() as d:
            write_memory(d, "feedback_alpha", "alpha", "See [[feedback_beta]].")
            write_memory(d, "feedback_beta", "beta", "No links here.")
            result = subprocess.run(
                [
                    sys.executable,
                    str(helpers_dir / "memory_health_check.py"),
                    "--quick",
                    "--memory-dir",
                    d,
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)

    def test_missing_memory_dir_is_a_config_error(self):
        result = subprocess.run(
            [
                sys.executable,
                str(helpers_dir / "memory_health_check.py"),
                "--quick",
                "--memory-dir",
                "/tmp/this-memory-dir-does-not-exist-ce-2-49",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
