#!/usr/bin/env python3
"""Tests for .claude/hooks/plugin_cache_integrity.py (CE-2.101, for CH-281.3).

The live hooks run from Claude Code's plugin cache. This check compares that
cache with `git archive` of the commit it was installed from, and refuses when
they differ. Every test builds its own world in a temp dir -- a home with a
plugin registry, a git checkout with a bare `origin`, and an installed cache
-- and never reads or writes the real ~/.claude.

Run directly: python3 .claude/hooks/tests/test_plugin_cache_integrity.py
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, HOOKS)
import plugin_cache_integrity as pci  # noqa: E402

MARKET = "demo-market"
PLUGIN = "demo-plugin"
KEY = f"{PLUGIN}@{MARKET}"


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


class World:
    """A home, a marketplace checkout pushed to a bare origin, and a cache
    installed from one commit of it."""

    def __init__(self, case):
        self.root = tempfile.mkdtemp(prefix="pci-")
        case.addCleanup(self._cleanup)
        self.home = os.path.join(self.root, "home")
        self.plugins_dir = os.path.join(self.home, ".claude", "plugins")
        os.makedirs(self.plugins_dir)
        self.origin = os.path.join(self.root, "origin.git")
        self.checkout = os.path.join(self.root, "checkout")
        _git(self.root, "init", "-q", "--bare", self.origin)
        _git(self.root, "init", "-q", "-b", "develop", self.checkout)
        _git(self.checkout, "config", "user.email", "t@example.test")
        _git(self.checkout, "config", "user.name", "t")
        self._write("checkout", ".claude-plugin/marketplace.json", json.dumps({
            "name": MARKET,
            "plugins": [{"name": PLUGIN, "source": f"./plugins/{PLUGIN}"}]}))
        self._write("checkout", f"plugins/{PLUGIN}/hooks/guard.py", "print('guard')\n")
        self._write("checkout", f"plugins/{PLUGIN}/cli/tool.py", "print('tool')\n")
        self._write("checkout", f"plugins/{PLUGIN}/bin/run", "#!/bin/sh\necho run\n")
        os.chmod(os.path.join(self.checkout, f"plugins/{PLUGIN}/bin/run"), 0o755)
        _git(self.checkout, "add", "-A")
        _git(self.checkout, "commit", "-q", "-m", "one")
        _git(self.checkout, "remote", "add", "origin", self.origin)
        _git(self.checkout, "push", "-q", "origin", "develop")
        _git(self.checkout, "fetch", "-q", "origin")
        self.sha = _git(self.checkout, "rev-parse", "HEAD")
        self.cache = os.path.join(self.plugins_dir, "cache", MARKET, PLUGIN, "1.0.0")
        self.install(self.sha)
        self.registry(self.sha)
        self.pinned = {MARKET: self.checkout}

    def _cleanup(self):
        for dirpath, dirnames, _ in os.walk(self.root):
            for d in dirnames:
                try:
                    os.chmod(os.path.join(dirpath, d), 0o755)
                except OSError:
                    pass
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, where, rel, text):
        base = self.checkout if where == "checkout" else self.cache
        path = os.path.join(base, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)

    def install(self, sha):
        """What `claude plugin install` leaves: the plugin's files at `sha`."""
        if os.path.exists(self.cache):
            shutil.rmtree(self.cache)
        os.makedirs(self.cache)
        raw = subprocess.run(["git", "archive", sha, f"plugins/{PLUGIN}"], cwd=self.checkout,
                             capture_output=True, check=True).stdout
        prefix = f"plugins/{PLUGIN}/"
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            for m in tar.getmembers():
                if not m.isfile() or not m.name.startswith(prefix):
                    continue
                dest = os.path.join(self.cache, m.name[len(prefix):])
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as fh:
                    fh.write(tar.extractfile(m).read())
                os.chmod(dest, m.mode & 0o777)

    def registry(self, sha, location=None, extra_markets=None, extra_plugins=None):
        with open(os.path.join(self.plugins_dir, "installed_plugins.json"), "w") as fh:
            plugins = {KEY: [{"scope": "user", "installPath": self.cache,
                              "version": "1.0.0", "gitCommitSha": sha}]}
            plugins.update(extra_plugins or {})
            json.dump({"version": 2, "plugins": plugins}, fh)
        with open(os.path.join(self.plugins_dir, "known_marketplaces.json"), "w") as fh:
            markets = {MARKET: {"source": {"source": "directory", "path": location or self.checkout},
                                "installLocation": location or self.checkout}}
            markets.update(extra_markets or {})
            json.dump(markets, fh)

    def check(self):
        return pci.check(home=self.home, pinned=self.pinned)


class TestACleanCachePasses(unittest.TestCase):

    def test_a_cache_matching_its_pushed_sha_passes(self):
        w = World(self)
        # Python leaves bytecode beside imported modules; it is deleted, not trusted.
        os.makedirs(os.path.join(w.cache, "hooks", "__pycache__"))
        with open(os.path.join(w.cache, "hooks", "__pycache__", "guard.cpython-312.pyc"), "wb") as fh:
            fh.write(b"real bytecode, still not trusted")
        ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))
        self.assertFalse(os.path.exists(os.path.join(w.cache, "hooks", "__pycache__")))
        self.assertIn(KEY, "\n".join(lines))

    def test_a_plugin_from_elsewhere_is_named_unverifiable(self):
        w = World(self)
        not_git = os.path.join(w.root, "plain-market")
        os.makedirs(not_git)
        w.registry(w.sha,
                   extra_markets={"plain": {"source": {"source": "directory", "path": not_git},
                                            "installLocation": not_git}},
                   extra_plugins={"other@plain": [{"installPath": os.path.join(w.root, "x"),
                                                   "version": "1", "gitCommitSha": w.sha}]})
        ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))
        text = "\n".join(lines)
        self.assertIn("other@plain", text)
        self.assertIn("unverifiable", text)


class TestDriftRefuses(unittest.TestCase):

    def _refused(self, w, path_fragment):
        ok, lines = w.check()
        text = "\n".join(lines)
        self.assertFalse(ok, f"drift in {path_fragment} passed")
        self.assertIn(path_fragment, text)
        self.assertIn("claude plugin update", text)

    def test_each_kind_of_drift_refuses_naming_the_path(self):
        cases = {
            "changed": lambda w: w._write("cache", "hooks/guard.py", "print('tampered')\n"),
            "missing": lambda w: os.remove(os.path.join(w.cache, "cli", "tool.py")),
            "extra": lambda w: w._write("cache", "hooks/planted.py", "print('x')\n"),
            "symlink": lambda w: (os.remove(os.path.join(w.cache, "cli", "tool.py")),
                                  os.symlink(os.path.join(w.checkout, f"plugins/{PLUGIN}/cli/tool.py"),
                                             os.path.join(w.cache, "cli", "tool.py"))),
            "exec bit": lambda w: os.chmod(os.path.join(w.cache, "bin", "run"), 0o644),
        }
        where = {"changed": "hooks/guard.py", "missing": "cli/tool.py", "extra": "hooks/planted.py",
                 "symlink": "cli/tool.py", "exec bit": "bin/run"}
        for name, tamper in cases.items():
            with self.subTest(name):
                w = World(self)
                tamper(w)
                self._refused(w, where[name])


class TestBytecodeIsNeverTrusted(unittest.TestCase):

    def test_a_forged_pyc_is_deleted_not_trusted(self):
        w = World(self)
        pyc = os.path.join(w.cache, "hooks", "__pycache__", "guard.cpython-312.pyc")
        os.makedirs(os.path.dirname(pyc))
        with open(pyc, "wb") as fh:
            fh.write(b"a forged module whose header matches its source")
        ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))
        self.assertFalse(os.path.exists(pyc), "a .pyc survived the check, so it was trusted")
        # A parallel worker's import rebuilds bytecode between the deletion and
        # the compare: that drift alone is deleted and compared once more.
        real_delete = pci._delete_bytecode
        calls = {"n": 0}

        def delete_then_rebuild(path):
            real_delete(path)
            calls["n"] += 1
            if calls["n"] == 1:
                os.makedirs(os.path.dirname(pyc), exist_ok=True)
                with open(pyc, "wb") as fh:
                    fh.write(b"rebuilt by a sibling import")
        with mock.patch.object(pci, "_delete_bytecode", delete_then_rebuild):
            ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))
        self.assertEqual(calls["n"], 2, "the check did not delete and compare once more")
        self.assertFalse(os.path.exists(pyc))

    def test_an_undeletable_pycache_refuses(self):
        w = World(self)
        pycache = os.path.join(w.cache, "hooks", "__pycache__")
        os.makedirs(pycache)
        with open(os.path.join(pycache, "guard.cpython-312.pyc"), "wb") as fh:
            fh.write(b"x")
        os.chmod(pycache, 0o555)  # its entries cannot be removed
        ok, lines = w.check()
        self.assertFalse(ok, "an undeletable __pycache__ passed")
        self.assertIn("__pycache__", "\n".join(lines))


class TestProvenance(unittest.TestCase):

    def test_an_unpushed_sha_refuses_naming_the_push(self):
        w = World(self)
        w._write("checkout", f"plugins/{PLUGIN}/hooks/guard.py", "print('local only')\n")
        _git(w.checkout, "commit", "-q", "-am", "never pushed")
        local = _git(w.checkout, "rev-parse", "HEAD")
        w.install(local)
        w.registry(local)
        ok, lines = w.check()
        text = "\n".join(lines)
        self.assertFalse(ok, "a commit on no remote branch passed")
        self.assertIn(local[:12], text)
        self.assertIn("push", text)
        # Control: the pushed commit it came from passes.
        w.install(w.sha)
        w.registry(w.sha)
        ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))

    def test_a_missing_sha_refuses_naming_a_reinstall(self):
        w = World(self)
        w.registry("0" * 40)
        ok, lines = w.check()
        text = "\n".join(lines)
        self.assertFalse(ok)
        self.assertIn("reinstall", text)


class TestTheRegistryIsNotRedirected(unittest.TestCase):

    def test_the_home_comes_from_the_password_database(self):
        import pwd
        real = pwd.getpwuid(os.getuid()).pw_dir
        with mock.patch.dict(os.environ, {"HOME": "/tmp/elsewhere",
                                          "CLAUDE_CONFIG_DIR": "/tmp/elsewhere/.claude"}):
            self.assertEqual(pci.passwd_home(), real)
            seen = {}

            def fake_check_home(home, pinned):
                seen["home"] = home
                return True, []
            with mock.patch.object(pci, "_check_home", fake_check_home):
                pci.check()
        self.assertEqual(seen["home"], real, "check() read the registry from a redirected home")

    def test_a_moved_install_location_refuses(self):
        w = World(self)
        moved = os.path.join(w.root, "someone-elses-checkout")
        shutil.copytree(w.checkout, moved)
        w.registry(w.sha, location=moved)
        ok, lines = w.check()
        text = "\n".join(lines)
        self.assertFalse(ok, "a marketplace moved off its pinned checkout passed")
        self.assertIn(w.checkout, text)

    def test_a_missing_or_unreadable_registry_refuses(self):
        for name in ("installed_plugins.json", "known_marketplaces.json"):
            for broken in ("missing", "unreadable"):
                with self.subTest(name=name, broken=broken):
                    w = World(self)
                    path = os.path.join(w.plugins_dir, name)
                    if broken == "missing":
                        os.remove(path)
                    else:
                        with open(path, "w") as fh:
                            fh.write("{not json")
                    ok, lines = w.check()
                    self.assertFalse(ok, f"a {broken} {name} passed")
                    self.assertIn(name, "\n".join(lines))


if __name__ == "__main__":
    unittest.main(verbosity=2)
