"""Tests for helpers/park-work.sh (CE-2.78)."""

import pathlib
import shutil
import subprocess
import tempfile
import unittest


W = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = W / "helpers" / "park-work.sh"


class TestTheSnapshot(unittest.TestCase):
    def _init_repo(self):
        repo = tempfile.mkdtemp()
        self.addCleanup(_rmtree, repo)

        def git(*args, **kw):
            return subprocess.run(
                ["git", *args], cwd=repo, check=True, capture_output=True
            )

        git("init", "-q")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "Test")
        (pathlib.Path(repo) / ".gitignore").write_text("out/*.bin\n")
        (pathlib.Path(repo) / "plain.txt").write_text("plain\n")
        out = pathlib.Path(repo) / "out"
        out.mkdir()
        (out / "kept.bin").write_bytes(b"original\n")
        git("add", ".gitignore", "plain.txt")
        git("add", "-f", "out/kept.bin")
        git("commit", "-q", "-m", "base")
        return repo

    def _park(self, repo):
        subprocess.run(
            ["bash", str(SCRIPT), "test-slug"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        refs = subprocess.run(
            [
                "git",
                "for-each-ref",
                "refs/parked",
                "--format=%(refname)",
            ],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.split()
        self.assertEqual(len(refs), 1, refs)
        return refs[0]

    def test_a_tracked_file_that_matches_gitignore_is_kept(self):
        repo = self._init_repo()
        (pathlib.Path(repo) / "out" / "kept.bin").write_bytes(b"replaced\n")
        (pathlib.Path(repo) / "new.txt").write_text("new\n")
        ref = self._park(repo)
        shown = subprocess.run(
            ["git", "show", f"{ref}:out/kept.bin"],
            cwd=repo,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(shown, b"replaced\n")

    def test_a_deletion_and_a_new_ignored_file_stay_out(self):
        repo = self._init_repo()
        (pathlib.Path(repo) / "plain.txt").unlink()
        (pathlib.Path(repo) / "out" / "extra.bin").write_bytes(b"extra\n")
        ref = self._park(repo)

        deleted = subprocess.run(
            ["git", "cat-file", "-e", f"{ref}:plain.txt"],
            cwd=repo,
            capture_output=True,
        )
        self.assertNotEqual(deleted.returncode, 0, "deleted plain.txt is in the ref")

        extra = subprocess.run(
            ["git", "cat-file", "-e", f"{ref}:out/extra.bin"],
            cwd=repo,
            capture_output=True,
        )
        self.assertNotEqual(extra.returncode, 0, "new ignored out/extra.bin is in the ref")

        kept = subprocess.run(
            ["git", "cat-file", "-e", f"{ref}:out/kept.bin"],
            cwd=repo,
            capture_output=True,
        )
        self.assertEqual(kept.returncode, 0, "out/kept.bin missing from the ref")


def _rmtree(path):
    shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
