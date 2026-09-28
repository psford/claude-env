#!/usr/bin/env python3
"""Check the installed plugin cache against the commit it was installed from.

CE-2.101, the first half of CH-281.3. The live hooks run from Claude Code's
plugin cache (~/.claude/plugins/cache/...). Edit and Write there are refused,
but Bash and anything it runs can still write there, and a changed hook in the
cache is a changed guard. This compares every verifiable plugin's cache with
`git archive` of the commit recorded in installed_plugins.json, and refuses
when they differ.

A plugin is verifiable when its marketplace is a directory source whose
installLocation is the top of a git checkout, and its record carries a
gitCommitSha. Any other plugin is named as unverifiable, never skipped
silently. A pinned marketplace (PINNED) must be verifiable, at its pinned path.

Provenance: the recorded commit must be reachable from origin/develop or
origin/main. A local branch proves nothing -- an agent moves one with
`git commit`.

Every __pycache__ in the cache is deleted before the compare, which then
excludes nothing. A forged .pyc whose header matches its source would
otherwise load unchecked.

Stated limits: a tripwire, not proof. This file, PINNED, the SessionStart
wiring and glm-agent are writable by the same account through Bash, and a
forged refs/remotes/origin/* inside .git defeats provenance offline.

Exit 0 when everything verifiable matches, 2 with the reason on stderr
otherwise. Any crash exits 2.

Usage: python3 plugin_cache_integrity.py
"""
import hashlib
import io
import json
import os
import posixpath
import pwd
import re
import stat
import subprocess
import sys
import tarfile
import traceback

GIT = "/usr/bin/git"
PINNED = {"psford-harness": "/home/patrick/projects/claude-harness"}
# Full ref names: a local branch called origin/develop would win over the
# remote-tracking ref if the short name were used.
REMOTE_REFS = ("refs/remotes/origin/develop", "refs/remotes/origin/main")
REGISTRY = ("installed_plugins.json", "known_marketplaces.json")
SHA = re.compile(r"[0-9a-f]{40}")


class Refused(Exception):
    pass


def passwd_home():
    """The account's home from the password database. $HOME and
    CLAUDE_CONFIG_DIR are ignored: a command prefix sets either."""
    return pwd.getpwuid(os.getuid()).pw_dir


def check(home=None, pinned=PINNED):
    """(ok, lines). Reads the registry under `home`, or the passwd home."""
    if home is None:
        home = passwd_home()
    return _check_home(home, pinned)


def _git(repo, *args):
    # GIT_DIR, GIT_WORK_TREE and the rest would point git somewhere else.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run([GIT, "-C", repo, *args], capture_output=True, env=env)


def _load(plugins_dir, name):
    path = os.path.join(plugins_dir, name)
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise Refused(f"cannot read {path}: {exc}") from None
    if not isinstance(data, dict):
        raise Refused(f"{path} is not a JSON object")
    return data


def _check_home(home, pinned):
    plugins_dir = os.path.join(home, ".claude", "plugins")
    try:
        installed = _load(plugins_dir, "installed_plugins.json")
        markets = _load(plugins_dir, "known_marketplaces.json")
        plugins = installed.get("plugins")
        if not isinstance(plugins, dict):
            raise Refused(f"{os.path.join(plugins_dir, 'installed_plugins.json')} has no plugins object")
    except Refused as exc:
        return False, [f"BLOCKED: the plugin registry cannot be read. {exc}",
                       "  Reinstall the plugins, or restore the file."]

    failures, verified, unverifiable = [], [], []

    for market, want in pinned.items():
        entry = markets.get(market)
        if isinstance(entry, dict) and _location(entry) != os.path.normpath(want):
            failures.append(
                f"marketplace {market} is installed from {_location(entry)!r}, "
                f"not its pinned checkout {want}.\n"
                f"  Re-add it from {want}, then claude plugin update.")

    for key, records in sorted(plugins.items()):
        market = key.rsplit("@", 1)[-1]
        for record in records if isinstance(records, list) else [records]:
            try:
                why_not = _unverifiable(key, market, record, markets, pinned)
                if why_not and market in pinned:
                    raise Refused(f"{key}: pinned marketplace {market} cannot be verified: {why_not}")
                if why_not:
                    unverifiable.append(f"{key}: {why_not}")
                    continue
                sha = _verify(key, record, _location(markets[market]))
                verified.append(f"{key} at {sha[:12]}")
            except Refused as exc:
                failures.append(str(exc))
            except OSError as exc:
                failures.append(f"{key}: {exc}")

    lines = []
    if failures:
        lines.append("BLOCKED: the installed plugin cache does not match its source.")
        lines.extend(f"- {f}" for f in failures)
    lines.extend(f"verified: {v}" for v in verified)
    lines.extend(f"unverifiable (not checked): {u}" for u in unverifiable)
    return not failures, lines


def _location(entry):
    loc = entry.get("installLocation")
    return os.path.normpath(loc) if isinstance(loc, str) and loc else None


def _unverifiable(key, market, record, markets, pinned):
    """Why this plugin cannot be checked, or None when it can."""
    entry = markets.get(market)
    if not isinstance(entry, dict):
        return f"marketplace {market} is not in known_marketplaces.json"
    source = entry.get("source")
    if not isinstance(source, dict) or source.get("source") != "directory":
        return f"marketplace {market} is not a directory source"
    loc = _location(entry)
    if loc is None:
        return f"marketplace {market} has no installLocation"
    top = _git(loc, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or os.path.normpath(top.stdout.decode().strip()) != loc:
        return f"{loc} is not the top of a git checkout"
    if not isinstance(record, dict) or not record.get("gitCommitSha"):
        return "its install record has no gitCommitSha"
    if not isinstance(record.get("installPath"), str):
        return "its install record has no installPath"
    return None


def _verify(key, record, loc):
    sha = record["gitCommitSha"]
    install_path = record["installPath"]
    reinstall = f"  Fix: reinstall it (claude plugin uninstall {key}, then claude plugin install {key})."
    if not SHA.fullmatch(sha) or _git(loc, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
        raise Refused(f"{key}: its recorded commit {sha[:12]} is not in {loc}.\n{reinstall}")
    if not any(_git(loc, "merge-base", "--is-ancestor", sha, ref).returncode == 0
               for ref in REMOTE_REFS):
        raise Refused(
            f"{key}: its recorded commit {sha[:12]} is on neither origin/develop nor "
            f"origin/main, so nothing outside this machine has it.\n"
            f"  Push it first (git -C {loc} push origin develop), then "
            f"claude plugin update {key}.")

    expected = _archive(key, sha, loc)
    try:
        _delete_bytecode(install_path)
        drift = _diff(expected, install_path)
        if drift and all("__pycache__" in path.split("/") for _, path in drift):
            # A parallel worker's import rebuilt bytecode after the delete.
            _delete_bytecode(install_path)
            drift = _diff(expected, install_path)
    except OSError as exc:
        raise Refused(f"{key}: cannot clear bytecode in {install_path}: {exc}") from None
    if drift:
        listed = "\n".join(f"    {kind}: {path}" for kind, path in drift)
        raise Refused(
            f"{key}: {install_path} differs from git archive {sha[:12]} of {loc}:\n"
            f"{listed}\n"
            f"  Put the change in git and push it, then claude plugin update {key}.")
    return sha


def _archive(key, sha, loc):
    """{relative path: ("file", sha256, executable) | ("link", target)} for
    the plugin's source at `sha`, read from git, never from the working tree."""
    shown = _git(loc, "show", f"{sha}:.claude-plugin/marketplace.json")
    if shown.returncode != 0:
        raise Refused(f"{key}: {sha[:12]} has no .claude-plugin/marketplace.json in {loc}")
    try:
        manifest = json.loads(shown.stdout)
    except ValueError as exc:
        raise Refused(f"{key}: marketplace.json at {sha[:12]} is not JSON: {exc}") from None
    name = key.rsplit("@", 1)[0]
    entries = [p for p in manifest.get("plugins", []) if isinstance(p, dict) and p.get("name") == name]
    source = entries[0].get("source") if len(entries) == 1 else None
    if not isinstance(source, str):
        raise Refused(f"{key}: marketplace.json at {sha[:12]} names no single local source for {name}")
    path = posixpath.normpath(source)
    if path.startswith(("/", "..", "-")):
        raise Refused(f"{key}: its source {source!r} lies outside {loc}")

    args = ["archive", "--format=tar", sha] + ([] if path == "." else [path])
    raw = _git(loc, *args)
    if raw.returncode != 0:
        raise Refused(f"{key}: git archive {sha[:12]} {path} failed: {raw.stderr.decode().strip()}")
    prefix = "" if path == "." else path + "/"
    expected = {}
    with tarfile.open(fileobj=io.BytesIO(raw.stdout)) as tar:
        for m in tar.getmembers():
            if not m.name.startswith(prefix) or m.isdir():
                continue
            rel = m.name[len(prefix):]
            if m.isfile():
                digest = hashlib.sha256(tar.extractfile(m).read()).hexdigest()
                expected[rel] = ("file", digest, bool(m.mode & 0o111))
            elif m.issym():
                expected[rel] = ("link", m.linkname)
            else:
                expected[rel] = ("special",)
    return expected


def _actual(install_path):
    found = {}
    if not os.path.isdir(install_path) or os.path.islink(install_path):
        raise Refused(f"the install path {install_path} is not a directory")
    for dirpath, dirnames, filenames in os.walk(install_path):
        for name in dirnames + filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, install_path).replace(os.sep, "/")
            st = os.lstat(full)
            if stat.S_ISLNK(st.st_mode):
                found[rel] = ("link", os.readlink(full))
            elif stat.S_ISREG(st.st_mode):
                with open(full, "rb") as fh:
                    digest = hashlib.sha256(fh.read()).hexdigest()
                found[rel] = ("file", digest, bool(st.st_mode & 0o111))
            elif not stat.S_ISDIR(st.st_mode):
                found[rel] = ("special",)
    return found


def _diff(expected, install_path):
    actual = _actual(install_path)
    drift = []
    for rel in sorted(set(expected) | set(actual)):
        want, got = expected.get(rel), actual.get(rel)
        if want == got:
            continue
        if got is None:
            drift.append(("missing", rel))
        elif want is None:
            drift.append(("extra", rel))
        elif got[0] != want[0]:
            drift.append((f"a {got[0]} where git has a {want[0]}", rel))
        elif got[0] == "file" and got[1] == want[1]:
            drift.append(("executable bit differs", rel))
        else:
            drift.append(("changed", rel))
    return drift


def _delete_bytecode(path):
    """Remove every __pycache__ under `path`. Raises OSError when one cannot
    be removed. One already gone (a parallel check) is not an error."""
    targets = []
    for dirpath, dirnames, _ in os.walk(path):
        if "__pycache__" in dirnames:
            targets.append(os.path.join(dirpath, "__pycache__"))
            dirnames.remove("__pycache__")
    for target in targets:
        if os.path.islink(target):
            os.remove(target)
            continue
        for dirpath, dirnames, filenames in os.walk(target, topdown=False):
            for name in filenames:
                _remove(os.remove, os.path.join(dirpath, name))
            for name in dirnames:
                full = os.path.join(dirpath, name)
                _remove(os.remove if os.path.islink(full) else os.rmdir, full)
        _remove(os.rmdir, target)


def _remove(fn, path):
    try:
        fn(path)
    except FileNotFoundError:
        pass


def main():
    try:
        ok, lines = check()
    except BaseException:
        print("BLOCKED: plugin_cache_integrity crashed, and refuses rather than pass.",
              file=sys.stderr)
        traceback.print_exc()
        return 2
    print("\n".join(lines), file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
