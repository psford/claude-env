# Infosec review — reply_rule_guard round 3 (CE-2.59)

**Range reviewed:** `git diff 49fd9ce..68156ae`, branch `dev/CE-2.56` —
`.claude/hooks/reply_rule_guard.py`, `helpers/reply_rule_check.py`,
`helpers/memory_health_check.py`, `helpers/data/reply_rule_checks.json`,
`helpers/tests/test_reply_rule_check.py`, `tooling-manifest.json`.
**Prior review:** `docs/reviews/2026-09-21-reply-rule-guard-infosec.md`
(range `49fd9ce..90995ad`), five findings.
**Date:** 2026-09-22. **Reviewer:** CSO (on demand; gates nothing).

## 1. Summary

I re-read the five files at 68156ae, ran the suite and the scanners, and
reproduced every round-1 finding's closure and every new suspicion through
`check()` itself: a loopback recorder standing in for `api.typesafe.ai`
captured the exact egress through the real `TypeSafeClient.ask`, a loopback
black hole timed the hot path, and 503/refused loopbacks measured the retry
ladder. No real API call was made in any reproduction. The full script is
`/home/patrick/.cache/cso-reply-rule-round3/repro.py` (nothing in it leaves
the machine).

The round-1 read was "a speed bump, not a fence." Four of its five findings
are now genuinely closed — most beyond what I asked for: the format-bypassable
gate was not documented, it was **deleted and the un-gated population was
measured** (150 non-question replies); fail-open paths are announced with a
reason and exit 1; egress is capped at 4000 chars and scrubbed before the
cut, with an honest `_about`; the hang is bounded to one 10-second attempt
with the dead final backoff removed for every caller; the committed personal
text and session IDs are gone. What survives is one specific descendant of
round-1 finding 2: **data that is neutered but valid still passes silently**
— `checks: []`, an inflated threshold, or a swapped question in the tracked
JSON gives a silent clean exit with no commit and no notice. That is the one
thing I would fix before registering the hook. The scrub also has measurable
boundary gaps (a separator-bearing `AccountKey=` leaks most of its
characters), and the registration itself — still pending — carries a trap in
the sibling hooks' `test -f … || exit 0` pattern.

## 2. Round-1 findings: closure status

| # | Round-1 finding | Status | Closed at |
|---|-----------------|--------|-----------|
| 1 | Last-line-`?` gate is agent-controlled shape (High) | **Closed** — gate deleted, un-gated population measured | `helpers/reply_rule_check.py:165-166`, data `reply_rule_checks.json:1062` (`statement_set`) |
| 2 | Silent fail-open via agent-reachable inputs (High) | **Closed for broken inputs; one neutered-input variant survives** → new finding A | `helpers/reply_rule_check.py:169-197, 213-215`, hook `.claude/hooks/reply_rule_guard.py:72-75`; survivor at `reply_rule_check.py:173-174, 208` |
| 3 | Unbounded, unredacted, understated egress (Medium) | **Closed** — 4000-char cap, scrub before cut, honest `_about`; boundary gaps → new finding B | `reply_rule_check.py:58, 80-95, 98-101`, data `reply_rule_checks.json:2` |
| 4 | 10.6-minute hang, hardcoded timeout (Medium) | **Closed in code** — `retries=1, timeout=10`, no dead final sleep; registration half still open → new finding C | `helpers/memory_health_check.py:136, 156, 166-167, 173-174`, `reply_rule_check.py:150-152` |
| 5 | Personal text / session IDs / machine-local path committed (Low) | **Closed** | `helpers/tests/test_reply_rule_check.py:31-49, 349-350`, `reply_rule_check.py:40-50` |

### Finding 1 — closed, beyond what was asked

The gate is gone: `check()` short-circuits only an empty reply
(`helpers/reply_rule_check.py:165-166`), and the docstring states it
(`:6-7` "Every non-empty reply is checked -- there is no shape gate"). Where
round 1 asked for the boundary to be *documented*, CE-2.56 instead funded
the measurement round 1 said the decision needed: a `statement_set` of 150
non-question replies (`reply_rule_checks.json:1062`), clean max 0.65 against
the unchanged 0.83 threshold, with the two sub-threshold objections recorded
honestly in `known_misses`. Reproduction (repro section A):

```
  question last (control)          : status=fired    calls_to_jev=1
  trailing line after the question : status=fired    calls_to_jev=1
  no question mark at all          : status=fired    calls_to_jev=1
  question inside closing quote    : status=fired    calls_to_jev=1
```

All four shapes that round 1 showed suppressing the check now reach the
classifier and fire. The residual is the recorded one — two known
statement-shape objections score below threshold (0.78-0.81, 0.67-0.71) —
which is a measured trade stated in the data file, not a hole.

### Finding 2 — closed for broken inputs; one variant survives (→ finding A)

Every "cannot run" path now returns `unchecked` with a plain reason, and the
hook turns that into `reply NOT checked -- <reason>` on stderr with exit 1
(`reply_rule_guard.py:72-75`), which Claude Code surfaces as a non-blocking
hook error. Reproduction (repro section B):

```
  no key                : status=unchecked reason='no classifier key: TYPESAFE_API_KEY not set…'
  corrupted checks JSON : status=unchecked reason='could not read checks data file: Expecting property name…'
  deleted memory note   : status=unchecked reason='missing memory note for rule feedback_ask_on_the_board_and_wait'
  classifier error      : status=unchecked reason='classifier did not answer: exhausted retries: HTTP 503'
```

Locations: `reply_rule_check.py:169-172` (unreadable checks), `:176-181`
(no key), `:191-197` (missing/unreadable memory note — including a
distinct `OSError` detail), `:213-215` (classifier failure), plus
CE-2.57's transcript handling in the hook (`:55-66` — unreadable transcript
and no-reply-text both announced, closing the empty-reply silent pass).
Note the implemented surface is per-session stderr + exit 1, not the
persistent log file round 1 suggested; that is a sound surface — the
degradation is visible in the session where it happens — provided the
neutered-input variant below is also closed, because that one produces no
output at all.

### Finding 3 — closed

`make_state` scrubs the whole reply then keeps its last 4000 characters
(`reply_rule_check.py:98-101`, `MAX_STATE_CHARS = 4000` at `:58`) — scrub
before cut, so a secret straddling the cut cannot be half-sent. `scrub`
(`:80-95`) handles home paths, Bearer tokens, key=value assignments, emails,
and long mixed alphanumeric runs. The data file's `_about`
(`reply_rule_checks.json:2`) now states the boundary round 1 asked for:
"what IS sent to Jev on every reply is at most its last 4000 characters,
scrubbed of secret-shaped strings." Reproduction through the real client
against a loopback recorder (repro section C):

```
  >5000-char reply -> request body bytes: 4478 (state 4000 chars)
    scrubbed /home/patrick                     : ABSENT
    scrubbed eyJhbGciOiJIUzI1NiJ5…(Bearer JWT) : ABSENT
    scrubbed S3cretPassValueHere               : ABSENT
    scrubbed ops@example.net                   : ABSENT
    scrubbed abcdefghij1234567890KQz9          : ABSENT
```

TLS to the real endpoint is default-verified and the Authorization header
carries only the API key, as before. The boundary gaps that remain are
finding B below.

### Finding 4 — closed in code

`ask()` takes `timeout` and `retries` parameters
(`helpers/memory_health_check.py:136`, used at `:156`), sleeps only between
attempts that can still retry (`:166-167`, `:173-174` — the dead post-final
sleep is gone for every caller), and batch callers keep today's defaults.
The guard's hot path calls with `retries=1, timeout=10`
(`helpers/reply_rule_check.py:150-152`). Reproduction (repro section D):

```
  ask(retries=1, timeout=10) vs black hole : elapsed 10.0s, raised: exhausted retries: timed out
  ask(retries=5) vs loopback 503           : sleeps=[1.7, 2.2, 4.5, 8.4] (n=4, between-attempts only;
                                             round 1 measured [1.5, 2.5, 4.5, 8.5, 16.8] incl. dead tail)
  hot-path params vs 503                   : elapsed 0.00s, zero sleeps
```

Worst case per reply is now ~10 s, inside the suite's "about 15 seconds"
AC. Two caveats: DNS resolution is not bounded by `urlopen`'s timeout, so
the per-hook registration timeout remains the backstop it always was (→
finding C), and — pre-existing, unchanged by this diff — a raw
`ConnectionResetError` during response read escapes the retry `except`
(it is neither `URLError` nor `TimeoutError`); the guard's broad except
converts it to `unchecked` (loud), but the batch memory tool would crash
on it.

### Finding 5 — closed

The test's memory fixture is synthetic — same shape (frontmatter
description + "How to apply" list), no quotation from Patrick
(`helpers/tests/test_reply_rule_check.py:31-49`, asserted at `:354-356`).
The data file contains no session identifiers (repro section E: no `session`
key anywhere in the JSON; asserted by the suite at `:349-350`); the labels
that remain (`clean` / `objected` / `flagged-by-rule`) are the calibration
ground truth, not identifiers. No `/home/patrick` literal in any of the four
new files: `default_memory_dir()` derives the Claude Code slug from the
checkout root with a `REPLY_RULE_MEMORY_DIR` override
(`helpers/reply_rule_check.py:40-50`). Residual, pre-existing and outside
this diff's hunks: `helpers/memory_health_check.py:57` still hardcodes the
`/home/patrick/...` memory path for its own batch use — the guard no longer
imports it, so the guard no longer no-ops on other machines, but the batch
tool still does.

## 3. New findings at a glance

| # | Area | Severity | Finding |
|---|------|----------|---------|
| A | Zero-trust / integrity | **High** | Neutered-but-valid checks data passes as clean, silently: `checks: []`, an inflated threshold, or a swapped question in the tracked JSON — one uncommitted working-tree edit, no notice at runtime |
| B | Data egress | Low | Scrub boundary gaps: most characters of a separator-bearing `AccountKey=` base64 leave verbatim; keys under 24 chars and letter-only hex runs pass whole |
| C | Availability / registration | Low | The hook is not yet registered; when it is, the sibling pattern (`test -f … \|\| exit 0`, no per-hook timeout decisions) would reintroduce a silent off switch |

## 4. Detailed new findings

### Finding A — neutered-but-valid checks data is still a silent off switch

**Location:** `helpers/reply_rule_check.py:173-174` (`if not checks: return
clean`), `:208` (`p >= c["threshold"]` — threshold from the same file),
`:204` (question from the same file); silent hook exit at
`.claude/hooks/reply_rule_guard.py:76` (clean → `return 0`, no output).
The data file is tracked, but the live hook reads the working tree, so no
commit is needed.
**Severity:** High — this is the surviving instance of round-1 finding 2's
shape ("no agent-usable bypass"): no approval surface, no runtime trace,
indistinguishable from a pass. Reachability: one `Edit`/`json.dump` against
`helpers/data/reply_rule_checks.json` in the checkout the hook is
registered against.

**Reproduction** (repro section B2 — neutered copies passed as
`checks_path`; the repo file itself was not touched):

```
  checks: []            : status=clean reason='' calls=0  <- hook: exit 0, prints NOTHING
  threshold 9.9         : status=clean reason='' calls=1  <- classifier consulted, can never fire
  question swapped      : status=clean reason='' calls=1  <- asks "is this about gardening?"
```

CE-2.56/CE-2.57 made *broken* loud; *neutered* still passes as valid. The
`REPLY_RULE_MEMORY_DIR` override is not a silencer by contrast — a bogus
dir yields `unchecked` (loud), and a valid note only alters the block text,
never whether the block fires.

**Mitigation:** two layers, both cheap.
1. One line now: `checks: []` is never a normal operating state — return
   `unchecked` ("checks data file has no checks") instead of `clean` at
   `reply_rule_check.py:173-174`.
2. The real fix, at registration time: pin the measured data. Put a
   `--checks-sha256 <hash>` argument (or equivalent) in the registered
   command in `~/.claude/settings.json` and have the hook verify the file
   against it, announcing a mismatch as `unchecked`. Editing the hash then
   means editing `settings.json` — which, per round 1, prompts Patrick —
   so re-measuring a check legitimately passes through his approval
   surface, and neutering it invisibly no longer exists. Editing the
   helper's own `.py` remains possible, as it does for every hook in this
   repo; the difference being closed here is data that the runtime treats
   as measured ground truth while looking like tuning.

### Finding B — scrub boundary: what "scrubbed of secret-shaped strings" does not catch

**Location:** `helpers/reply_rule_check.py:64-67` (`SECRET_ASSIGN_RE` word
list requires `\b(password|…|key)\b` — `AccountKey=` has no word boundary
before "Key"), `:69` (`LONG_TOKEN_RE` needs a 24+ char unbroken
`[A-Za-z0-9_-]` run), `:72-77` (a run must contain both a letter and a
digit).
**Severity:** Low — transmission is still the feature, the cap and the
honest `_about` are the real mitigations, and the reply's author can always
encode around any list (this is hygiene against incidental leakage, not an
exfiltration boundary — nothing in the docs should read it as one).

**Reproduction** (repro section C, boundary probes, same loopback client):

```
    Azure AccountKey, no +/ separators   : REDACTED (LONG_TOKEN catches the unbroken run)
    Azure AccountKey, WITH +/= separators: ~33 of 86 key chars SENT VERBATIM
        scrubbed -> '…AccountKey=JX7Zk/R9mQvP+2wL5nE8yT3aHf6/dS1gU4bC0oKiMq7+[redacted]==;…'
    20-char sk- key                      : SENT VERBATIM ('sk-live-abcdef123456')
    letter-only hex run                  : SENT VERBATIM ('deadbeefcafedeadbeefcafedead')
```

**Mitigation:** add `accountkey`, `connectionstring`, `sig`, `sas` to the
`SECRET_ASSIGN_RE` word list (or match a `*key` suffix: `\b\w*key\b`), which
redacts the whole value regardless of the base64's separators; optionally
lower nothing else — the 24-char floor and letter+digit rule are reasonable
false-positive trades. One sentence in `_about` ("scrubbed of *common*
secret shapes, best-effort") keeps the promise matched to the mechanism.

### Finding C — registration is still pending, and the sibling pattern is a trap

**Location:** `~/.claude/settings.json` Stop hooks (outside the repo) —
`reply_rule_guard` is absent; its registered siblings
(`absolute_path_link_guard`, `verification_claim_guard`) use
`test -f <hook> || exit 0` with `timeout` 10–15.
**Severity:** Low (it is a decision not yet taken, not a defect in the
reviewed code — but two of the three ways to take it wrong reintroduce
round-1 findings).

**Reproduction:** `python3 -c "import json; print(json.dumps(json.load(open('/home/patrick/.claude/settings.json'))['hooks']['Stop'], indent=1))"`
— no reply_rule_guard entry exists; both siblings' commands begin with
`test -f … || exit 0`.

**Mitigation:** when CE-2.56/2.57 merge and the hook is registered:
1. Give it a `timeout` of ~15 s or more (one 10 s attempt plus overhead).
   `urlopen`'s timeout does not bound DNS, so the registration timeout is
   the only backstop for that corner.
2. Do **not** copy the siblings' `test -f … || exit 0` prefix: for this
   guard, a deleted hook file must not be a silent pass — that is the exact
   shape round-1 finding 2 existed to forbid. Register the command bare (it
   lives on this machine's main checkout, where merged), so a missing file
   is a loud hook error.
3. Fold in finding A's `--checks-sha256` pin — the same registration edit.

## 5. What the scanners said

| Check | Result |
|---|---|
| tests-all-run (scoped to `helpers/tests`, suite glob) | covered — every discovered test file executed, counts match, nothing skipped |
| test suite direct run | 12/12 pass (`Ran 12 tests … OK`), ~0.14 s |
| gitleaks (repo-wide, via scan wrapper) | 7 findings, all pre-existing and outside this diff — `.secrets.baseline` self-matches ×4, `key-vault-role-assignment.bicep`, `verify_azure_deploy.py`, bicep modules README — the identical set round 1 reported |
| semgrep (`--config auto`, 3 source files) | 1 audit: `dynamic-urllib-use-detected` at `memory_health_check.py:156` — false positive; the URL is the module constant `TYPESAFE_URL`, reply text is the POST body and never reaches the URL |
| osv-scanner / npm audit | no manifest (stdlib-only Python, no `package.json`/lockfile) — skipped, not passed |

Reproduction script (loopback-only, nothing real sent):
`/home/patrick/.cache/cso-reply-rule-round3/repro.py`.

## 6. Recommended order

1. **Finding A, layer 1** (the one-line `checks: []` → `unchecked` fix) —
   the only surviving High; everything else from round 1 is closed.
2. **Finding C together with finding A, layer 2** — one registration edit
   carries the timeout, the no-`|| exit 0` decision, and the checks-file
   hash pin; doing them separately invites the sibling-pattern copy-paste.
3. **Finding B** — one regex word-list line plus one honest `_about`
   sentence; mechanical, whenever convenient before or after registration.
