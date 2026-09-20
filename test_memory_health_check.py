#!/usr/bin/env python3
"""
Unit tests for helpers/memory_health_check.py (CE-2.49)

Tests for:
- Dead [[link]] detection, and that a ticket-id-shaped [[link]] is excluded
- Dead cited-path detection, narrowed to backtick-quoted ~/ and /home/ paths
- load_memories skipping MEMORY.md and parsing frontmatter description + body
- The CLI's --quick, --memory-dir and exit-code contract end to end
- The overlap pass ranking pairs from a stubbed TypeSafe response (no
  network call) and recording that response's usage/cost figures
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import the module to test
helpers_dir = Path(__file__).parent / "helpers"
sys.path.insert(0, str(helpers_dir))
from memory_health_check import (  # noqa: E402
    TYPESAFE_COST_PER_INPUT_TOKEN,
    TypeSafeClient,
    find_dead_links,
    find_dead_paths,
    load_memories,
    overlap_pairs,
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


class _StubHTTPResponse:
    """Stands in for the `with urllib.request.urlopen(...) as r:` response."""

    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestOverlapPairs(unittest.TestCase):
    """AC1's token-cost clause: the overlap pass ranks pairs from whatever
    TypeSafe answers, and records that answer's usage figures -- covered
    here by stubbing urllib.request.urlopen so no real API call is made."""

    def test_overlap_pairs_scores_from_stub_and_records_usage(self):
        memories = [
            {"key": "feedback_a", "desc": "ends the turn on a question"},
            {"key": "feedback_b", "desc": "waits on the board for an answer"},
            {"key": "feedback_c", "desc": "an unrelated third memory"},
        ]
        # One canned response per memory (overlap_pairs asks once per memory
        # against the others). feedback_a and feedback_b pick each other at
        # 0.93; feedback_c's best match scores below the 0.45 threshold.
        responses = iter(
            [
                {
                    "answers": {
                        "same": {
                            "type": "choice",
                            "choice": "feedback_b",
                            "confidence": 0.9,
                            "probabilities": {"feedback_b": 0.93, "feedback_c": 0.07},
                        }
                    },
                    "usage": {"input_tokens": 500, "output_tokens": 10},
                },
                {
                    "answers": {
                        "same": {
                            "type": "choice",
                            "choice": "feedback_a",
                            "confidence": 0.9,
                            "probabilities": {"feedback_a": 0.93, "feedback_c": 0.07},
                        }
                    },
                    "usage": {"input_tokens": 500, "output_tokens": 10},
                },
                {
                    "answers": {
                        "same": {
                            "type": "choice",
                            "choice": "feedback_b",
                            "confidence": 0.5,
                            "probabilities": {"feedback_a": 0.2, "feedback_b": 0.3},
                        }
                    },
                    "usage": {"input_tokens": 500, "output_tokens": 10},
                },
            ]
        )

        def fake_urlopen(request, timeout=None):
            return _StubHTTPResponse(next(responses))

        with patch("urllib.request.urlopen", fake_urlopen):
            client = TypeSafeClient(api_key="unused-stub-key")
            pairs = overlap_pairs(memories, client, threshold=0.45)

        # (a) the pass emits pairs carrying the scores the stub returned.
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["score"], 0.93)
        self.assertEqual({pairs[0]["a"], pairs[0]["b"]}, {"feedback_a", "feedback_b"})

        # (b) the usage/cost figures from the response are recorded.
        usage = client.cost_summary()
        self.assertEqual(usage["calls"], 3)
        self.assertEqual(usage["input_tokens"], 1500)
        self.assertEqual(usage["output_tokens"], 30)
        self.assertAlmostEqual(
            usage["cost_usd"], 1500 * TYPESAFE_COST_PER_INPUT_TOKEN, places=6
        )


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
