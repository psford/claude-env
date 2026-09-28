"""Tests for helpers/sync-user-settings.sh (CE-2.108)."""

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


W = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = W / "helpers" / "sync-user-settings.sh"


class TestTheSettingsMirror(unittest.TestCase):
    def test_the_mirror_matches_the_live_settings(self):
        """AC1: --check exits 0 when mirror matches live settings."""
        result = subprocess.run(
            ["bash", str(SCRIPT), "--check"],
            env={**os.environ, "CLAUDE_ENV_ROOT": str(W)},
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

    def test_a_drifted_mirror_fails_and_names_only_the_capture(self):
        """AC2: --check exits 3 with drift message naming only capture, not --restore."""
        # Create a temp CLAUDE_ENV_ROOT with an old mirror
        temp_env_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, temp_env_root)

        # Create infrastructure/claude-settings directory
        mirror_dir = pathlib.Path(temp_env_root) / "infrastructure" / "claude-settings"
        mirror_dir.mkdir(parents=True)

        # Write a stale mirror file
        mirror_file = mirror_dir / "user-settings.json"
        mirror_file.write_text(json.dumps({"stale": True}, indent=2) + "\n")

        # Run --check against the stale mirror
        result = subprocess.run(
            ["bash", str(SCRIPT), "--check"],
            env={**os.environ, "CLAUDE_ENV_ROOT": temp_env_root},
            capture_output=True,
            text=True,
        )

        # Assert exit 3
        self.assertEqual(result.returncode, 3, f"Expected exit 3, got {result.returncode}. stderr: {result.stderr}")

        # Assert output names sync-user-settings.sh
        combined_output = result.stderr + result.stdout
        self.assertIn("sync-user-settings.sh", combined_output)

        # Assert output does NOT contain --restore
        self.assertNotIn("--restore", combined_output)


def _rmtree(path):
    shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
