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
DEFAULT_REFS = ["refs/remotes/origin/develop", "refs/remotes/origin/main"]


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


class World:
    """A home, a marketplace checkout pushed to a bare origin, and a cache
    installed from one commit of it. `subdir` puts the marketplace in a
    subdirectory of the checkout; `branch` is the one branch pushed."""

    def __init__(self, case, subdir="", branch="develop"):
        self.root = tempfile.mkdtemp(prefix="pci-")
        case.addCleanup(self._cleanup)
        self.subdir = subdir
        self.branch = branch
        self.home = os.path.join(self.root, "home")
        self.plugins_dir = os.path.join(self.home, ".claude", "plugins")
        os.makedirs(self.plugins_dir)
        self.origin = os.path.join(self.root, "origin.git")
        self.checkout = os.path.join(self.root, "checkout")
        self.location = os.path.join(self.checkout, subdir) if subdir else self.checkout
        _git(self.root, "init", "-q", "--bare", self.origin)
        _git(self.root, "init", "-q", "-b", branch, self.checkout)
        _git(self.checkout, "config", "user.email", "t@example.test")
        _git(self.checkout, "config", "user.name", "t")
        self._write("checkout", self._rel(".claude-plugin/marketplace.json"), json.dumps({
            "name": MARKET,
            "plugins": [{"name": PLUGIN, "source": f"./plugins/{PLUGIN}"}]}))
        self._write("checkout", self._rel(f"plugins/{PLUGIN}/hooks/guard.py"), "print('guard')\n")
        self._write("checkout", self._rel(f"plugins/{PLUGIN}/cli/tool.py"), "print('tool')\n")
        self._write("checkout", self._rel(f"plugins/{PLUGIN}/bin/run"), "#!/bin/sh\necho run\n")
        os.chmod(os.path.join(self.checkout, self._rel(f"plugins/{PLUGIN}/bin/run")), 0o755)
        _git(self.checkout, "add", "-A")
        _git(self.checkout, "commit", "-q", "-m", "one")
        _git(self.checkout, "remote", "add", "origin", self.origin)
        _git(self.checkout, "push", "-q", "origin", branch)
        _git(self.checkout, "fetch", "-q", "origin")
        self.sha = _git(self.checkout, "rev-parse", "HEAD")
        self.cache = os.path.join(self.plugins_dir, "cache", MARKET, PLUGIN, "1.0.0")
        self.install(self.sha)
        self.registry(self.sha)
        refs = DEFAULT_REFS if branch in ("develop", "main") else [f"refs/remotes/origin/{branch}"]
        self.pinned = {MARKET: {"path": self.location, "refs": refs}}

    def _rel(self, path):
        return f"{self.subdir}/{path}" if self.subdir else path

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

    def commit(self, text, message, push=False, rel=None):
        """Write `rel` in the checkout (default: the plugin's guard.py),
        commit it, optionally push the branch; the new sha."""
        rel = rel or self._rel(f"plugins/{PLUGIN}/hooks/guard.py")
        self._write("checkout", rel, text)
        _git(self.checkout, "add", rel)
        _git(self.checkout, "commit", "-q", "-m", message)
        if push:
            _git(self.checkout, "push", "-q", "origin", self.branch)
            _git(self.checkout, "fetch", "-q", "origin")
        return _git(self.checkout, "rev-parse", "HEAD")

    def install(self, sha):
        """What `claude plugin install` leaves: the plugin's files at `sha`."""
        if os.path.exists(self.cache):
            shutil.rmtree(self.cache)
        os.makedirs(self.cache)
        source = self._rel(f"plugins/{PLUGIN}")
        raw = subprocess.run(["git", "archive", sha, source], cwd=self.checkout,
                             capture_output=True, check=True).stdout
        prefix = source + "/"
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
        location = location or self.location
        with open(os.path.join(self.plugins_dir, "installed_plugins.json"), "w") as fh:
            plugins = {KEY: [{"scope": "user", "installPath": self.cache,
                              "version": "1.0.0", "gitCommitSha": sha}]}
            plugins.update(extra_plugins or {})
            json.dump({"version": 2, "plugins": plugins}, fh)
        with open(os.path.join(self.plugins_dir, "known_marketplaces.json"), "w") as fh:
            markets = {MARKET: {"source": {"source": "directory", "path": location},
                                "installLocation": location}}
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
        local = w.commit("print('local only')\n", "never pushed")
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

    def test_deleted_pinned_rows_refuse(self):
        """The CSO's change review, finding 1: a well-formed registry with the
        pinned marketplace's rows deleted loads none of its hooks, and must
        not pass as checked."""
        def drop_plugin_record(w):
            with open(os.path.join(w.plugins_dir, "installed_plugins.json"), "w") as fh:
                json.dump({"version": 2, "plugins": {}}, fh)

        def empty_both(w):
            drop_plugin_record(w)
            with open(os.path.join(w.plugins_dir, "known_marketplaces.json"), "w") as fh:
                json.dump({}, fh)
        for name, tamper in (("plugin record deleted", drop_plugin_record),
                             ("both registries emptied", empty_both)):
            with self.subTest(name):
                w = World(self)
                tamper(w)
                ok, lines = w.check()
                self.assertFalse(ok, f"{name} passed")
                self.assertIn(MARKET, "\n".join(lines))


class TestReplaceObjectsAreNotHonored(unittest.TestCase):
    """CE-2.107, the CSO's finding 1 on CE-2.101 (High): `git replace` made
    `git archive` of an honest pushed sha yield another commit's tree, so an
    evil cache passed behind a truthful recorded sha."""

    def test_a_replaced_sha_refuses(self):
        w = World(self)
        evil = w.commit("print('EVIL payload')\n", "evil, never pushed")
        w.install(evil)       # the cache holds E's content
        w.registry(w.sha)     # the registry still records the honest pushed X
        _git(w.checkout, "replace", w.sha, evil)
        ok, lines = w.check()
        self.assertFalse(ok, "a cache behind a replaced sha passed:\n" + "\n".join(lines))

    def test_a_replace_ref_in_a_pinned_checkout_refuses(self):
        w = World(self)
        ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))
        other = w.commit("print('unrelated')\n", "a local commit")
        _git(w.checkout, "replace", other, w.sha)
        ok, lines = w.check()
        text = "\n".join(lines)
        self.assertFalse(ok, "a replace ref in the pinned checkout passed")
        self.assertIn(f"refs/replace/{other}", text)
        _git(w.checkout, "replace", "-d", other)
        ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))

    def test_an_unpinned_market_ignores_replace_too(self):
        """The CSO's change review of CE-2.107, finding 1: for an unpinned
        marketplace --no-replace-objects is the only defence, so it is
        pinned by its own test."""
        w = World(self)
        w.pinned = {}
        evil = w.commit("print('EVIL payload')\n", "evil, never pushed")
        w.install(evil)
        w.registry(w.sha)
        _git(w.checkout, "replace", w.sha, evil)
        ok, lines = w.check()
        self.assertFalse(ok, "an unpinned cache behind a replaced sha passed:\n" + "\n".join(lines))


class TestPinnedInstallsAreCurrent(unittest.TestCase):
    """CE-2.107, the CSO's finding 4 on CE-2.101: winding cache and registry
    back to any older pushed commit passed, so a pinned plugin could be loaded
    from before a guard was hardened. "Current" is judged by the plugin's
    files, not the head commit: a push outside the plugin needs no update, and
    `claude plugin update` would find nothing to install."""

    def _two_pushed(self):
        w = World(self)
        v1 = w.sha
        v2 = w.commit("print('guard v2')\n", "v2", push=True)
        return w, v1, v2

    def test_an_older_pushed_sha_refuses_for_a_pinned_market(self):
        w, v1, v2 = self._two_pushed()
        w.install(v1)
        w.registry(v1)
        ok, lines = w.check()
        text = "\n".join(lines)
        self.assertFalse(ok, "a pinned plugin rolled back to an older pushed sha passed")
        self.assertIn(v1[:12], text)
        self.assertIn("claude plugin update", text)

    def test_the_current_head_passes(self):
        w, v1, v2 = self._two_pushed()
        w.install(v2)
        w.registry(v2)
        ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))
        # The head of origin/main passes too, while develop has moved on.
        _git(w.checkout, "push", "-q", "origin", f"{v1}:refs/heads/main")
        _git(w.checkout, "fetch", "-q", "origin")
        w.install(v1)
        w.registry(v1)
        ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))

    def test_a_push_outside_the_plugin_keeps_it_current(self):
        w = World(self)
        head = w.commit("board code, not the plugin\n", "a push outside the plugin",
                        push=True, rel="dashboard/server.py")
        self.assertNotEqual(head, w.sha)
        ok, lines = w.check()   # still installed at the first commit
        self.assertTrue(ok, "a push outside the plugin made the install stale:\n" + "\n".join(lines))

    def test_an_unpinned_market_may_be_older(self):
        w, v1, v2 = self._two_pushed()
        w.pinned = {}
        w.install(v1)
        w.registry(v1)
        ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))


class TestNestedAndPerPinMarketplaces(unittest.TestCase):
    """CE-2.105: patricks-workflow@patricks-local lives in a subdirectory of
    ~/.claude's own checkout, whose one remote branch is master. Patrick chose
    to make it verifiable and pin it; the CSO's list review set the shape: pin
    the exact installLocation, carry each pin's remote refs, keep the default
    refs for unpinned marketplaces, and judge containment by real path."""

    def test_a_marketplace_inside_a_checkout_is_verified(self):
        w = World(self, subdir="plugins/marketplaces/local")
        ok, lines = w.check()
        self.assertTrue(ok, "\n".join(lines))
        self.assertIn(f"verified: {KEY}", "\n".join(lines))
        w._write("cache", "hooks/guard.py", "print('tampered')\n")
        ok, lines = w.check()
        self.assertFalse(ok, "drift in a nested marketplace's cache passed")
        self.assertIn("hooks/guard.py", "\n".join(lines))

    def test_its_install_location_is_pinned_exactly(self):
        w = World(self, subdir="plugins/marketplaces/local")
        other = os.path.join(w.checkout, "plugins", "marketplaces", "other")
        shutil.copytree(w.location, other)
        _git(w.checkout, "add", "-A")
        _git(w.checkout, "commit", "-q", "-m", "a second marketplace in the same checkout")
        _git(w.checkout, "push", "-q", "origin", w.branch)
        _git(w.checkout, "fetch", "-q", "origin")
        w.registry(w.sha, location=other)
        ok, lines = w.check()
        text = "\n".join(lines)
        self.assertFalse(ok, "a redirect to another directory in the pinned checkout passed")
        self.assertIn(w.location, text)

    def test_a_pin_uses_its_own_remote_refs(self):
        w = World(self, subdir="plugins/marketplaces/local", branch="master")
        self.assertEqual(w.pinned[MARKET]["refs"], ["refs/remotes/origin/master"])
        ok, lines = w.check()
        self.assertTrue(ok, "a pin on origin/master failed with neither develop nor main:\n"
                        + "\n".join(lines))

    def test_an_unpinned_market_keeps_the_default_refs(self):
        """The CSO's finding 1 (High): per-pin refs must not drop the
        ancestry judgment for marketplaces that have no pin."""
        w = World(self)
        w.pinned = {}
        local = w.commit("print('local only')\n", "never pushed")
        w.install(local)
        w.registry(local)
        ok, lines = w.check()
        self.assertFalse(ok, "an unpinned marketplace's unpushed sha passed")
        self.assertIn(local[:12], "\n".join(lines))

    def test_a_prefix_lookalike_is_not_inside(self):
        base = tempfile.mkdtemp(prefix="pci-inside-")
        self.addCleanup(shutil.rmtree, base, True)
        checkout = os.path.join(base, "checkout")
        evil = os.path.join(base, "checkout-evil")
        os.makedirs(os.path.join(checkout, "m"))
        os.makedirs(evil)
        self.assertTrue(pci._inside(os.path.join(checkout, "m"), checkout))
        self.assertTrue(pci._inside(checkout, checkout))
        self.assertFalse(pci._inside(evil, checkout),
                         "a path sharing only a string prefix counted as inside")
        link = os.path.join(base, "link-into")
        os.symlink(os.path.join(checkout, "m"), link)
        self.assertTrue(pci._inside(link, checkout), "containment did not follow the real path")

    def test_the_refusal_names_the_pins_branch(self):
        w = World(self, subdir="plugins/marketplaces/local", branch="master")
        local = w.commit("print('local only')\n", "never pushed")
        w.install(local)
        w.registry(local)
        ok, lines = w.check()
        text = "\n".join(lines)
        self.assertFalse(ok)
        self.assertIn("origin/master", text)
        self.assertIn("push origin master", text)
        self.assertNotIn("develop", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
