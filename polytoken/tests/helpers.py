"""Shared test helpers for the polytoken layer tests.

Self-contained on purpose: unittest-compatible (pytest also collects these
tests fine), no pytest fixtures, no network, no writes outside a temp dir.

Every test gets:
  - a sandbox HOME (so $HOME-relative state is isolated),
  - POLYTOKEN_STATE_HOME under that HOME,
  - a copy of the repo's polytoken/ layer (scripts under test run from it),
  - a stateful fake `gh` (issues live in JSONL; every argv is recorded),
  - a fake `polytoken` binary whose version env-var controls version checks.
"""

import json
import os
import shutil
import subprocess
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LAYER_SRC = os.path.join(REPO_ROOT, "polytoken")

FAKE_GH = r"""#!/usr/bin/env bash
# Stateful fake gh for tests. State in $FAKE_GH_HOME (issues.jsonl, calls.log).
set -u
D="${FAKE_GH_HOME:?FAKE_GH_HOME not set}"
mkdir -p "$D"
printf '%s\n' "$*" >> "$D/calls.log"

if [ "${FAKE_GH_HANG:-0}" = 1 ]; then sleep 30; exit 0; fi

cmd="${1:-}"; [ $# -gt 0 ] && shift
case "$cmd" in
  auth)
    printf 'Logged in to github.com account testsuite\n'; exit 0 ;;
  label)
    case "${1:-}" in
      list) printf 'todo\nin-progress\n' ;;
      create) : ;;
    esac
    exit 0 ;;
  issue)
    sub="${1:-}"; shift
    case "$sub" in
      list)
        if [ -f "$D/issues.jsonl" ]; then
          jq -s --arg label todo \
            '[ .[] | select(.state == "open" and (([.labels[]?.name] | index($label)) != null)) ]' \
            "$D/issues.jsonl" 2>/dev/null || printf '[]'
        else
          printf '[]'
        fi
        exit 0 ;;
      create)
        title=""; body=""; label=""
        while [ $# -gt 0 ]; do
          case "$1" in
            --title) title="$2"; shift 2 ;;
            --body)  body="$2";  shift 2 ;;
            --label) label="$2"; shift 2 ;;
            *) shift ;;
          esac
        done
        n=100
        [ -f "$D/issues.jsonl" ] && n=$(( 100 + $(wc -l < "$D/issues.jsonl") + 1 ))
        jq -cn --argjson n "$n" --arg t "$title" --arg b "$body" --arg l "$label" \
          '{number:$n, title:$t, body:$b, state:"open", labels:[{name:$l}]}' >> "$D/issues.jsonl"
        printf 'https://github.com/psford/claude-env/issues/%s\n' "$n"
        exit 0 ;;
      close)
        num=""
        while [ $# -gt 0 ]; do
          case "$1" in
            --repo|--comment) shift 2 ;;
            *) if [ -z "$num" ]; then num="$1"; fi; shift ;;
          esac
        done
        if [ -f "$D/issues.jsonl" ]; then
          tmp="$D/issues.jsonl.tmp"
          jq -c --argjson n "${num:-0}" \
            'if .number == $n then .state = "closed" else . end' \
            "$D/issues.jsonl" > "$tmp" && mv "$tmp" "$D/issues.jsonl"
        fi
        exit 0 ;;
      edit)
        num=""; title=""; addl=""; reml=""
        while [ $# -gt 0 ]; do
          case "$1" in
            --title)        title="$2"; shift 2 ;;
            --add-label)    addl="$2";  shift 2 ;;
            --remove-label) reml="$2";  shift 2 ;;
            --repo)         shift 2 ;;
            *) if [ -z "$num" ] && [ "${1#-}" = "$1" ]; then num="$1"; fi; shift ;;
          esac
        done
        if [ -f "$D/issues.jsonl" ]; then
          tmp="$D/issues.jsonl.tmp"
          jq -c --argjson n "${num:-0}" --arg t "$title" --arg a "$addl" --arg r "$reml" \
            'if .number == $n then (
               (if $t != "" then .title = $t else . end)
               | (if $a != "" then .labels = ((.labels + [{name:$a}]) | unique) else . end)
               | (if $r != "" then .labels = ([.labels[]? | select(.name != $r)]) else . end)
             ) else . end' \
            "$D/issues.jsonl" > "$tmp" && mv "$tmp" "$D/issues.jsonl"
        fi
        exit 0 ;;
    esac
    exit 0 ;;
esac
exit 0
"""

FAKE_POLYTOKEN = r"""#!/usr/bin/env bash
case "${1:-}" in
  --version) printf 'polytoken %s\n' "${FAKE_POLYTOKEN_VERSION:-0.8.17}"; exit 0 ;;
  doctor)
    printf '  ok skills - %s skill(s) discovered\n' "${FAKE_SKILLS:-4}"
    printf '  ok subagents - %s subagent(s) discovered\n' "${FAKE_SUBAGENTS:-4}"
    exit 0 ;;
esac
exit 0
"""


class Sandbox:
    def __init__(self, tmp, session_id="sess-test"):
        self.tmp = tmp
        self.home = os.path.join(tmp, "home")
        os.makedirs(self.home)
        self.state = os.path.join(self.home, ".local", "share", "polytoken")
        os.makedirs(os.path.join(self.state, "sessions-v1", session_id, "todos"), exist_ok=True)
        self.session_id = session_id
        self.layer = os.path.join(tmp, "clone", "claude-env", "polytoken")
        shutil.copytree(LAYER_SRC, self.layer)
        self.bin = os.path.join(tmp, "bin")
        os.makedirs(self.bin)
        self.gh_home = os.path.join(tmp, "ghstate")
        os.makedirs(self.gh_home)
        self.gh = self._write_bin("gh-fake", FAKE_GH)
        self.polytoken = self._write_bin("polytoken-fake", FAKE_POLYTOKEN)
        self.env = os.environ.copy()
        self.env.update({
            "HOME": self.home,
            "POLYTOKEN_STATE_HOME": self.state,
            "GH_BIN": self.gh,
            "POLYTOKEN_BIN": self.polytoken,
            "FAKE_GH_HOME": self.gh_home,
        })
        self.set_session(session_id)

    def _write_bin(self, name, content):
        path = os.path.join(self.bin, name)
        with open(path, "w") as fh:
            fh.write(content)
        os.chmod(path, 0o755)
        return path

    def set_session(self, session_id):
        self.session_id = session_id
        with open(os.path.join(self.state, "todo-session.current"), "w") as fh:
            fh.write(session_id)

    def clear_session(self):
        p = os.path.join(self.state, "todo-session.current")
        if os.path.exists(p):
            os.remove(p)

    # ------------------------------------------------------------- gh state
    @property
    def issues_path(self):
        return os.path.join(self.gh_home, "issues.jsonl")

    def issues(self):
        if not os.path.exists(self.issues_path):
            return []
        with open(self.issues_path) as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def calls(self):
        p = os.path.join(self.gh_home, "calls.log")
        if not os.path.exists(p):
            return []
        with open(p) as fh:
            return [line.rstrip("\n") for line in fh if line.strip()]

    def rewrite_issue(self, number, **fields):
        rows = self.issues()
        for row in rows:
            if row["number"] == number:
                row.update(fields)
        with open(self.issues_path, "w") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

    # -------------------------------------------------------- session todos
    def seed_todo(self, todo_id, title, status="pending"):
        d = os.path.join(self.state, "sessions-v1", self.session_id, "todos")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "%s.json" % todo_id), "w") as fh:
            json.dump({"id": todo_id, "title": title, "description": "",
                       "status": status, "dependencies": []}, fh)

    # -------------------------------------------------------------- logging
    def log_lines(self):
        p = os.path.join(self.state, "todo-sync.log")
        if not os.path.exists(p):
            return []
        with open(p) as fh:
            return [line.rstrip("\n") for line in fh if line.strip()]

    # ----------------------------------------------------------- run hooks
    def run_hook(self, script, event, env_extra=None, timeout=30):
        env = dict(self.env)
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["/bin/bash", os.path.join(self.layer, "hooks", script)],
            input=json.dumps(event), text=True, capture_output=True,
            env=env, timeout=timeout)

    def run_sync(self, event, **kw):
        return self.run_hook("todo-sync.sh", event, **kw)

    def run_restore(self, event, **kw):
        return self.run_hook("todo-restore.sh", event, **kw)

    def run_bootstrap(self, *args, env_extra=None, config_home=None, timeout=60):
        env = dict(self.env)
        if env_extra:
            env.update(env_extra)
        if config_home:
            env["POLYTOKEN_CONFIG_HOME"] = config_home
        return subprocess.run(
            ["/bin/bash", os.path.join(self.layer, "bootstrap.sh")] + list(args),
            text=True, capture_output=True, env=env, timeout=timeout)


def machine_name():
    out = subprocess.run(["bash", "-c", "hostname -s 2>/dev/null || hostname"],
                         capture_output=True, text=True)
    return out.stdout.strip()


def sandbox_factory():
    """Return a fresh Sandbox in a temp dir plus a cleanup callable."""
    tmp = tempfile.mkdtemp(prefix="ptlayer-")
    sb = Sandbox(tmp)
    return sb, lambda: shutil.rmtree(tmp, ignore_errors=True)
