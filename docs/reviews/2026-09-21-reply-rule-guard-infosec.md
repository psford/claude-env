# Infosec review — reply_rule_guard (Stop hook, CE-2.55)

**Range reviewed:** `git diff 49fd9ce..90995ad`, branch `dev/CE-2.55` —
`.claude/hooks/reply_rule_guard.py`, `helpers/reply_rule_check.py`,
`helpers/data/reply_rule_checks.json`, `helpers/tests/test_reply_rule_check.py`,
`tooling-manifest.json`.
**Date:** 2026-09-21. **Reviewer:** CSO (on demand; gates nothing).

## 1. Summary

I read the guard, its helper, the data file, the test suite, and the two modules
they lean on (`verification_claim_guard.last_assistant_text`,
`memory_health_check.TypeSafeClient` / `load_api_key`), then reproduced every
suspected hole locally: a loopback recorder standing in for `api.typesafe.ai`
captured the exact egress; a loopback black hole measured the per-attempt
timeout; the gate, threshold and fail-open paths were exercised through
`check_reply` itself. No real API call was made in any reproduction.

The guard does what it says on the compliant path: only a reply whose last
non-empty line ends in `?` is sent, one question is asked, the block quotes the
rule's own instruction, and the classifier fail-open is real. Against an
adversary, though, it is a speed bump, not a fence: the agent it exists to
catch can step around it for free by formatting (finding 1), or permanently and
invisibly switch it off with one edit to an untracked file (finding 2). Its
egress is broader than its data file admits (finding 3). QA's timeout question
has a definite answer: a registration timeout is necessary but not sufficient —
the retry ladder lives in code and must be sized for a synchronous hook
(finding 4). Nothing secret is committed, but private memory text and session
IDs are (finding 5).

## 2. Findings at a glance

| # | Area | Severity | Finding |
|---|------|----------|---------|
| 1 | Authz (of the guarded agent) | **High** | The last-line-`?` population gate is a shape the agent fully controls — any trailing line, or a closing quote after the `?`, sends nothing to Jev and fires nothing |
| 2 | Zero-trust / integrity | **High** | Fail-open is silent (no log, no stderr) and reachable permanently by agent-writable inputs: the untracked `.env` key line, a deleted memory note, a corrupted checks JSON |
| 3 | Data egress | Medium | Every question-ending reply in **every project** is transmitted verbatim and untruncated to a third party — secrets quoted in replies, absolute paths, names — while the data file says only "No reply text is stored" |
| 4 | Availability (hang) | Medium | `ask()` defaults to 5 × 120 s + ~34 s backoff ≈ 10.6 min per check, per reply; timeout hardcoded and caller-unsettable. A registration timeout alone converts the stall into the same silent fail-open, at the cap, every time the network is bad |
| 5 | Public-repo hygiene | Low | Private memory text verbatim in the test, 12 local session IDs + objection labels in the JSON, and a hardcoded `/home/patrick/...` memory path (guard silently no-ops on every other machine) |

## 3. Detailed findings

### Finding 1 — the gate is agent-controlled shape, so the adversary it exists for walks around it

**Location:** `helpers/reply_rule_check.py:60-71` (`ends_with_question`),
`helpers/reply_rule_check.py:123-124` (the gate in `check_reply`).
**Severity:** High (for the control's purpose). Reachability: trivial, purely
in-conversation, zero footprint — no file writes, no permissions, nothing in any
log.

**Reproduction** (via the suite's own fixtures and seam, loopback only):

```
python3 /home/patrick/.cache/cso-reply-rule-review/repro.py   # section B
  violating reply, question last        : fired=1 calls_to_jev=1
  same reply + any trailing line        : fired=0 calls_to_jev=0
  same reply, question inside quotes    : fired=0 calls_to_jev=0
```

A FakeClient scoring 0.99 — well over the 0.83 threshold — is never called the
moment the `?` is not the last character of the last non-empty line. `Standing
by.` after the question, or `?"` instead of `?`, both suppress the check
entirely. An agent that is *about to* ask Patrick a reserved decision in chat —
the exact adversary, the one under time pressure — pays nothing to comply with
the letter of the guard while defeating it. The guard's own docstring explains
why the gate exists: the question was calibrated only on last-line-question
replies, so widening the gate would run it off its measured population. That is
a real constraint, and it means this is a **design limitation to state, not a
regex to patch**. What it must not be is unstated: today nothing in the guard,
the data file, or the manifest tells the reader that the enforcement is
syntactic and therefore voluntary on the part of the entity it constrains.

**Mitigation:** none that keeps the calibration. Document the boundary in the
JSON `_about` and the hook docstring ("the gate is the measured population and
is format-bypassable; this guard catches the unthinking violation, not the
deliberate one"), and treat the human-visible signal — the absence of a
`ticket ask` for a decision — as the real control, as it is today.

### Finding 2 — silent fail-open plus agent-reachable kill switches = a deniable off switch

**Location:** `helpers/reply_rule_check.py:151-152` (`except Exception: return
[]` — no logging of any kind), `.claude/hooks/reply_rule_guard.py:40-42`
(nothing printed, exit 0, when `fired == []`), and the three inputs an agent
can touch without a commit:
- the API key path: `helpers/reply_rule_check.py:171-172` →
  `helpers/memory_health_check.py:192-204` (env var or the **untracked**
  `<repo>/.env`);
- the memory note: `helpers/reply_rule_check.py:131-135` (missing file → fail
  open) — and agents routinely create, rename and delete memory notes as a
  normal, legitimate operation;
- the checks data: `helpers/reply_rule_check.py:125-128` and the JSON itself —
  uncommitted edits to the working tree are what the live hook reads.

**Severity:** High. This is the shape Patrick's zero-trust norm ("no
agent-usable bypass") exists to forbid. Reachability: one file edit, no commit,
no approval surface dedicated to it (unlike `~/.claude/settings.json` edits,
which prompt him); the memory-note deletion is an action agents take
legitimately every week.

**Reproduction:**

```
python3 /home/patrick/.cache/cso-reply-rule-review/repro.py   # sections C1, C2
  check_reply with no key: fired=0 (fail open, no output)
  threshold 9.9 + score 0.93 -> fired=0 (client was still called 1x)
  corrupted JSON -> fired=0, no error raised
```

and reading `.claude/hooks/reply_rule_guard.py:40-42`: an empty `fired` list —
whether clean, keyless, or sabotaged — prints nothing and exits 0. Broken and
sabotaged are indistinguishable, forever, because nothing records which
happened. The docstring's availability argument ("a broken classifier must
never stop every reply") is sound; the silence is not. `rm` of
`~/.claude/projects/-home-patrick-projects-claude-env/memory/feedback_ask_on_the_board_and_wait.md`
— one line of Bash, inside an agent's normal lane — disables the guard for
every future reply on the machine.

**Mitigation:** keep fail-open, make it loud. In the `except` at
`reply_rule_check.py:151`, append one line (exception class, timestamp, rule
count) to a log under `~/.claude/` (stderr alone is harness-dependent for
exit-0 Stop hooks); in the hook, emit the same on the fail-open path. A guard
whose defeat is invisible invites defeat; a guard whose degradation shows up in
a file Patrick can glance at does not. Optionally: treat "checks file present
but unreadable/corrupt" differently from "key missing" — the former is never a
normal operating state.

### Finding 3 — every question-ending reply, every project, leaves the machine verbatim

**Location:** egress assembled at `helpers/memory_health_check.py:136-152`
(`ask`: `state` = the reply string as-is, `Authorization: Bearer <key>`,
`https://api.typesafe.ai/v1/systemone`, TLS default-verified — good), fed by
`helpers/reply_rule_check.py:106-110`, sourced by
`.claude/hooks/reply_rule_guard.py:40` via `last_assistant_text` (last assistant
message only — the Stop-hook stdin JSON, user messages and tool results are
*not* sent). Registration is planned global in `~/.claude/settings.json`, so
the population is every question-ending reply in **every session on the
machine**, across all repos.

**Severity:** Medium — transmission is the feature and the endpoint is one the
repo already pays to use, but three things exceed what the feature needs:
1. **No redaction.** Replies in this workflow routinely quote secrets under
   review (connection strings, key-shaped values), absolute paths (his own
   memory rule mandates absolute paths in chat links), and personal names.
2. **No bound.** A 1 MB reply is a 1,000,106-byte request body.
3. **The data file understates the boundary.** `reply_rule_checks.json:2` says
   "No reply text is stored" — true of the local file, silent on the fact that
   the text is transmitted off-machine, which a reader could take for a privacy
   property the design does not have.

**Reproduction** (loopback recorder, dummy key — nothing real sent):

```
python3 /home/patrick/.cache/cso-reply-rule-review/repro.py   # section D
  state == full reply verbatim: True
    egress contains 'HUNTER2-live': True
    egress contains 'sk-live-abcdef123456': True
    egress contains '/home/<user>/projects/<app>/logs': True   [path generalised 2026-09-22, CE-2.65: the stale-path scan]
  1 MB reply -> request body bytes: 1000106
```

**Mitigation, in order of value per line:** (a) fix the `_about` line to say
what is transmitted and to whom; (b) cap the state (e.g. last ~8 KB — the
question is about the reply's ask, which lives at its end); (c) if replies in
secret-bearing workflows (this review's own among them) will regularly quote
credentials, consider a cheap local redaction pass over obvious key shapes
before transmission. The trust boundary to name out loud: TypeSafe receives a
feed of question-ending replies across all of Patrick's projects; a compromised
or simply curious endpoint operator sees that stream.

### Finding 4 — QA's hang: the registration timeout is necessary, not sufficient; the code must change too

**Location:** `helpers/memory_health_check.py:142-170` — `retries=5` default,
`timeout=120` hardcoded inside `urlopen` at line 152 (not a parameter),
exponential backoff sleeps even after the final attempt (the ladder ends
1.5 + 2.5 + 4.5 + 8.5 + 16.8 ≈ 34 s, the last ~17 s of which are slept *after*
the last try, just to raise); consumed with defaults by
`helpers/reply_rule_check.py:106-110`; run once per check, serially, per reply
(`reply_rule_check.py:140-141`).

**Severity:** Medium (availability, plus it feeds finding 2's silence).

**Reproduction** (loopback black hole; and the except-path driven directly):

```
A1: retries=1 against a hanging loopback listener:
    elapsed 121.5s, raised: exhausted retries: timed out
    -> the 120 s per-attempt timeout is hardcoded, not caller-settable
A2: retries=5 on instant failures:
    sleep ladder executed (incl. a dead final sleep before raise):
      [1.47, 2.47, 4.53, 8.5, 16.8]
    worst case with a hanging service: 5 x 120s + 33.77s = 633.77s = 10.6 min
    per ask(), per check, per reply
```

That matches QA's ~10 minutes. A per-hook `timeout` in the registration fixes
the *stall* — the runner kills the hook at the cap and a killed Stop hook emits
no block JSON, so the reply proceeds. But that is all it fixes, and it does so
by making every degraded-network reply burn the full cap and then fail open
silently — the guard provides zero protection exactly when the service is
unreachable, and (per finding 2) nobody learns the difference. It also leaves
`ask()`'s sizing wrong for any future hot-path consumer, and leaves the
~17 s of dead final backoff asleep inside any budget a hook timeout grants.

**Mitigation:** do both.
1. **Code:** make `ask(..., timeout=120, retries=5)` parameters (batch callers
   like `memory_health_check` keep today's values untouched), and have
   `score_check` call with `retries=1, timeout≈10` — one short attempt, no
   backoff, on the hot path of every reply. Sleep only *between* attempts that
   can still retry (drop the post-loop sleep). If more checks are ever added,
   the serial per-check loop multiplies the worst case — single-attempt keeps
   N checks inside N×10 s.
2. **Registration:** set the per-hook `timeout` (e.g. 30 s) as the outer
   backstop for the unkillable-case (DNS stall, weird socket states) — a
   backstop, not the primary control.

### Finding 5 — machine-local and private content in a repo served from a public URL

**Location and severity: Low each.** gitleaks is clean on all four new files —
no secrets committed. What is committed:
- `helpers/tests/test_reply_rule_check.py:25-52` — a private memory note
  verbatim (`ASK_ON_THE_BOARD_MEMORY`), including direct personal quotes from
  Patrick about a months-long friction. Personal content, published.
- `helpers/data/reply_rule_checks.json` — no reply text (verified), but 12
  local Claude Code session IDs (`2f3eadc2`, `010af701`, …) plus per-reply
  labels of which of his replies he "objected" to. Behavioral metadata about
  his own interactions, published.
- `helpers/reply_rule_check.py:36-38` — `LIVE_MEMORY_DIR` hardcoded to
  `/home/patrick/.claude/projects/...` (copied from
  `memory_health_check.py:56-58` rather than imported — a second copy of a
  machine-local constant; on any machine but his, `load_memory` returns None
  and the guard silently no-ops, including for every non-psford user the
  tooling manifest serves).

**Mitigation:** trim the test fixture to the frontmatter description + a
two-line invented "How to apply" (the loader only needs the shape, and the
suite's claim to "verbatim" fixtures is about the *replies*, which contain no
personal content); strip or hash the session IDs in the JSON (`session:
"s-2f3e"` loses nothing measurable); resolve the memory dir from
`~/.claude/projects/<slug>/memory` or an env var with the current path as
documented default, imported from one place.

## 4. What the scanners said

| Check | Result |
|---|---|
| tests-all-run (`helpers/tests/test_reply_rule_check.py`) | 7/7 executed, 7/7 pass, none skipped |
| tests-all-run, repo-wide | `tests/test_endpoint_hooks.py` (46 tests) errors on discovery under bare `python3` — needs `pytest`, which isn't installed there. **Pre-existing, untouched by this diff**, noted for the record |
| gitleaks (4 new files) | 0 findings |
| gitleaks (repo-wide, via scan wrapper) | 7 pre-existing `generic-api-key` hits (`.secrets.baseline` self-matches ×4, `key-vault-role-assignment.bicep`, `verify_azure_deploy.py`, bicep README) — all outside this diff |
| semgrep (3 new source files) | 0 findings |
| osv-scanner / npm audit | no applicable manifest (stdlib-only Python, no `package.json`/lockfile) — skipped, not passed |

Reproduction script (nothing in it leaves the machine): 
`/home/patrick/.cache/cso-reply-rule-review/repro.py`.

## 5. Recommended order

1. **Finding 4 (code) together with the registration** — it is the change QA is
   already waiting on, it is small, parameterizing `ask()` touches no batch
   caller's behavior, and shipping the hook with a kill-at-cap timeout but the
   old ladder burns ~17 s of every capped budget asleep for nothing.
2. **Finding 2 (make fail-open loud)** — one `except`-path log line; until it
   exists, findings 1 and 2 combine into "an agent can defeat this forever and
   invisibly," which is the property Patrick's zero-trust norm forbids.
3. **Finding 5 (public-repo trims)** — mechanical, before merge to `main`,
   while the diff is still open; retrofitting published personal text later
   means history rewrites.
4. **Finding 3 (egress documentation + size cap)** — the `_about` sentence is a
   one-line honesty fix; the cap and any redaction can follow.
5. **Finding 1 (state the design limit)** — a sentence in two docstrings; the
   decision it forces (accept a voluntary guard, or fund measuring a question
   on the un-gated population) is Patrick's, not this review's.
