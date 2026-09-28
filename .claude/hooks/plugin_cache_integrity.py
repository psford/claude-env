#!/usr/bin/env python3
"""Check the installed plugin cache against the commit it was installed from.

CE-2.101, the first half of CH-281.3. The live hooks run from Claude Code's
plugin cache (~/.claude/plugins/cache/...). Edit and Write there are refused,
but Bash and anything it runs can still write there, and a changed hook in the
cache is a changed guard. This compares every verifiable plugin's cache with
`git archive` of the commit recorded in installed_plugins.json, and refuses
when they differ.

A plugin is verifiable when its marketplace is a directory source whose
installLocation is inside (or is the top of) a git checkout, and its record
carries a gitCommitSha. Any other plugin is named as unverifiable, never
skipped silently. Containment is judged on real paths with commonpath, never
a string prefix (CE-2.105).

A pinned marketplace (PINNED) must be installed from its exact pinned
installLocation, be present in the registry, and have at least one plugin
verified: a registry with its rows deleted loads none of its hooks, and must
not pass as checked. Each pin names the remote refs it answers to
(CE-2.105): psford-harness answers to origin/develop and origin/main, and
patricks-local, which lives in ~/.claude's own checkout, to origin/master.
Unpinned verifiable marketplaces answer to DEFAULT_REFS.

Provenance: the recorded commit must be reachable from one of those refs. A
local branch proves nothing -- an agent moves one with `git commit`. For a
pinned marketplace the plugin must also be CURRENT (CE-2.107): its files at
the recorded commit must equal its files at one of the pin's remote heads.
Otherwise a rollback to any older pushed commit passes. Judged by the
plugin's tree, not the head commit: a push outside the plugin needs no
update, and `claude plugin update`, which follows the version, would find
nothing to install.

git runs with --no-replace-objects and an empty graft file (CE-2.107): a
`git replace` made `git archive` of an honest pushed sha yield another
commit's tree. A pinned checkout holding any replace ref refuses outright.

Every __pycache__ in the cache is deleted before the compare, which then
excludes nothing. A forged .pyc whose header matches its source would
otherwise load unchecked.

Stated limits: a tripwire, not proof. This file, PINNED, the SessionStart
wiring and glm-agent are writable by the same account through Bash, and a
forged refs/remotes/origin/* inside .git defeats provenance offline. The
check's own bytecode deletion is a write to the cache: a future cache
write-guard must exempt it. At SessionStart a refusal is only a notice
(CE-2.103); glm-agent's before-and-after check is the gate for workers.
"Current" accepts any of a pin's refs, by design: the plugin as of the last
release merged to main also passes, so the guards can be wound back to that
release, never further. ~/.claude is pushed by hand: a reinstall of
patricks-workflow from an unpushed commit refuses until it is pushed.

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
# Full ref names: a local branch called origin/develop would win over the
# remote-tracking ref if the short name were used.
DEFAULT_REFS = ("refs/remotes/origin/develop", "refs/remotes/origin/main")
PINNED = {
    "psford-harness": {"path": "/home/patrick/projects/claude-harness",
                       "refs": list(DEFAULT_REFS)},
    "patricks-local": {"path": "/home/patrick/.claude/plugins/marketplaces/patricks-local",
                       "refs": ["refs/remotes/origin/master"]},
}
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
    # Grafts rewrite parents, and so what counts as an ancestor.
    env["GIT_GRAFT_FILE"] = os.devnull
    return subprocess.run([GIT, "--no-replace-objects", "-C", repo, *args],
                          capture_output=True, env=env)


def _inside(child, parent):
    """True when `child` is `parent` or below it, on real paths. A shared
    string prefix (checkout vs checkout-evil) is not containment."""
    child, parent = os.path.realpath(child), os.path.realpath(parent)
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False


def _short(ref):
    return ref[len("refs/remotes/"):] if ref.startswith("refs/remotes/") else ref


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

    # The CSO's change review of CE-2.105, finding 2: a malformed pin refuses
    # by name, before anything indexes into it.
    bad = [m for m, p in pinned.items()
           if not (isinstance(p, dict) and isinstance(p.get("path"), str) and p["path"]
                   and isinstance(p.get("refs"), list) and p["refs"]
                   and all(isinstance(r, str) and r.startswith("refs/remotes/") for r in p["refs"]))]
    if bad:
        return False, ["BLOCKED: the installed plugin cache cannot be checked."] + [
            f"- the pin for {m} is malformed: it needs a path and a non-empty list of "
            f"refs/remotes/... refs. Fix PINNED in {os.path.abspath(__file__)}." for m in bad]

    failures, verified, unverifiable = [], [], []
    failed_markets, verified_markets = set(), set()

    for market, pin in pinned.items():
        entry = markets.get(market)
        want = os.path.normpath(pin["path"])
        if isinstance(entry, dict) and _location(entry) != want:
            failed_markets.add(market)
            failures.append(
                f"marketplace {market} is installed from {_location(entry)!r}, "
                f"not its pinned location {want}.\n"
                f"  Re-add it from {want}, then claude plugin update.")

    for key, records in sorted(plugins.items()):
        market = key.rsplit("@", 1)[-1]
        pin = pinned.get(market)
        for record in records if isinstance(records, list) else [records]:
            try:
                why_not = _unverifiable(key, market, record, markets)
                if why_not and pin is not None:
                    raise Refused(f"{key}: pinned marketplace {market} cannot be verified: {why_not}")
                if why_not:
                    unverifiable.append(f"{key}: {why_not}")
                    continue
                sha = _verify(key, record, _location(markets[market]), pin)
                verified.append(f"{key} at {sha[:12]}")
                verified_markets.add(market)
            except (Refused, OSError) as exc:
                failed_markets.add(market)
                failures.append(str(exc) if isinstance(exc, Refused) else f"{key}: {exc}")

    # The CSO's change review, finding 1: presence is part of the pin.
    for market, pin in pinned.items():
        if market in failed_markets or market in verified_markets:
            continue
        want = pin["path"]
        if not isinstance(markets.get(market), dict):
            failures.append(
                f"the pinned marketplace {market} is missing from known_marketplaces.json, "
                f"so none of its hooks load and nothing of it was checked.\n"
                f"  Re-add it from {want} and reinstall its plugins, or restore the "
                f"registry: it was changed outside claude plugin.")
        else:
            failures.append(
                f"no plugin from the pinned marketplace {market} is recorded in "
                f"installed_plugins.json, so none of its hooks load and nothing of it "
                f"was checked.\n"
                f"  Reinstall its plugins (claude plugin install <plugin>@{market}), or "
                f"restore the registry: it was changed outside claude plugin.")

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


def _top(loc):
    """The top of the git checkout `loc` sits in, or None."""
    got = _git(loc, "rev-parse", "--show-toplevel")
    if got.returncode != 0:
        return None
    top = os.path.normpath(got.stdout.decode().strip())
    return top if _inside(loc, top) else None


def _unverifiable(key, market, record, markets):
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
    if _top(loc) is None:
        return f"{loc} is not inside a git checkout"
    if not isinstance(record, dict) or not record.get("gitCommitSha"):
        return "its install record has no gitCommitSha"
    if not isinstance(record.get("installPath"), str):
        return "its install record has no installPath"
    return None


def _verify(key, record, loc, pin):
    sha = record["gitCommitSha"]
    install_path = record["installPath"]
    refs = tuple(pin["refs"]) if pin is not None else DEFAULT_REFS
    top = _top(loc)
    if top is None:
        raise Refused(f"{key}: {loc} is no longer inside a git checkout")
    rel = os.path.relpath(os.path.realpath(loc), os.path.realpath(top)).replace(os.sep, "/")
    reinstall = f"  Fix: reinstall it (claude plugin uninstall {key}, then claude plugin install {key})."
    if not SHA.fullmatch(sha) or _git(top, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
        raise Refused(f"{key}: its recorded commit {sha[:12]} is not in {top}.\n{reinstall}")
    if pin is not None:
        replaced = _git(top, "for-each-ref", "--format=%(refname)", "refs/replace/")
        if replaced.returncode != 0 or replaced.stdout.strip():
            names = replaced.stdout.decode().split() or ["(for-each-ref failed)"]
            raise Refused(
                f"{key}: {top} holds replace refs, which rewrite what git reads for a "
                f"commit: {', '.join(names)}.\n"
                f"  Delete them (git -C {top} replace -d <sha>), then run this check again.")
    if not any(_git(top, "merge-base", "--is-ancestor", sha, ref).returncode == 0 for ref in refs):
        branch = refs[0].rsplit("/", 1)[-1]
        raise Refused(
            f"{key}: its recorded commit {sha[:12]} is on none of "
            f"{', '.join(_short(r) for r in refs)}, so nothing outside this machine has it.\n"
            f"  Push it first (git -C {top} push origin {branch}), then "
            f"claude plugin update {key}.")
    path = _source_path(key, sha, top, rel)
    if pin is not None:
        _require_current(key, sha, top, path, refs)

    expected = _archive(key, sha, top, path)
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


def _tree(top, commit, path):
    """The tree id of `path` at `commit`, or None when it has none."""
    spec = f"{commit}^{{tree}}" if path == "." else f"{commit}:{path}"
    got = _git(top, "rev-parse", "--verify", "--quiet", spec)
    return got.stdout.decode().strip() if got.returncode == 0 else None


def _require_current(key, sha, top, path, refs):
    """The plugin's files at `sha` must be its files at one of the refs' heads."""
    mine = _tree(top, sha, path)
    heads = {}
    for ref in refs:
        got = _git(top, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if got.returncode == 0:
            head = got.stdout.decode().strip()
            heads[_short(ref)] = (head, _tree(top, head, path))
    if mine is None or not any(tree == mine for _, tree in heads.values()):
        shown = ", ".join(f"{name} at {head[:12]}" for name, (head, _) in heads.items()) or "none found"
        raise Refused(
            f"{key}: the plugin at its recorded commit {sha[:12]} is not the plugin at a "
            f"current head ({shown}), so an older version of it is loaded.\n"
            f"  Update it: claude plugin update {key}.")


def _source_path(key, sha, top, rel):
    """The plugin's directory, repo-relative, read from marketplace.json at
    `sha` -- never from the working tree. `rel` is the marketplace's own
    directory within the checkout ("." at the top)."""
    base = "" if rel == "." else rel + "/"
    shown = _git(top, "show", f"{sha}:{base}.claude-plugin/marketplace.json")
    if shown.returncode != 0:
        raise Refused(f"{key}: {sha[:12]} has no {base}.claude-plugin/marketplace.json in {top}")
    try:
        manifest = json.loads(shown.stdout)
    except ValueError as exc:
        raise Refused(f"{key}: marketplace.json at {sha[:12]} is not JSON: {exc}") from None
    name = key.rsplit("@", 1)[0]
    entries = [p for p in manifest.get("plugins", []) if isinstance(p, dict) and p.get("name") == name]
    source = entries[0].get("source") if len(entries) == 1 else None
    if not isinstance(source, str) or source.startswith("/"):
        raise Refused(f"{key}: marketplace.json at {sha[:12]} names no single local source for {name}")
    path = posixpath.normpath(posixpath.join(rel, source))
    within = posixpath.normpath(rel)
    if path.startswith(("/", "..", "-")) or (
            within != "." and path != within and not path.startswith(within + "/")):
        raise Refused(f"{key}: its source {source!r} lies outside its marketplace {rel}")
    return path


def _archive(key, sha, top, path):
    """{relative path: ("file", sha256, executable) | ("link", target)} for
    the plugin's source at `sha`, read from git, never from the working tree."""
    args = ["archive", "--format=tar", sha] + ([] if path == "." else [path])
    raw = _git(top, *args)
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
