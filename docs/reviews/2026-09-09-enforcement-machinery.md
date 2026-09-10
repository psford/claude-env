# Code-quality review: the enforcement machinery

**Reviewer:** Grace (context-free review, `psford-tickets:grace`)
**Requested by:** Patrick, 2026-09-09, following an unauthorised change to a control
**Reviewed:** `claude-env` at `origin/develop` `0d1ede2`; `claude-harness` at `origin/develop` `9ca5813`
**Suites green at review time:** `run-hook-tests.sh` → `ALL 200 HOOK TESTS PASSED`;
`python3 -m unittest discover -s tests` in `plugins/psford-tickets` → `OK`

Grace was given the scope and nothing else — no conversation, no tickets, no account of the
incident. Her report is reproduced as written.

---

## 1. Summary

This is the best-reasoned control code I have read in a long time, and a substantial amount of
it does not do what it says. Those two facts are not in tension — they have the same cause.
Almost every guard here was written in response to a real incident, and the comment above it
names the date and the damage. What is missing is the second half of that discipline: after
fixing the instance, going and finding the class. The repo's own rules demand exactly that
("AUDIT THE CLASS"), and the code keeps not doing it.

The shape you asked me to hunt for is here, and it is not one guard — it is a pattern with three
faces. **First**, one shell parser exists twice, in two repos, and the copies have drifted in
opposite directions, so each carries a hole the other fixed; a backslash-newline defeats six
harness gates including Patrick's UAT verdict, and a one-letter flag transposition (`bash -cl`
versus `bash -lc`) defeats a different set in each repo. **Second**, the fixture corpus tests the
branches somebody was burned by and not the others: `main_branch_guard` has 35 green fixtures,
all about push refspecs, while four of its destructive refusals are broken and its three SQL
refusals are dead code that no realistic invocation can reach. **Third**, there are twenty-five
agent-typable bypass tokens across the live control surface, most of them printed to the agent
inside the very refusal that was supposed to stop it — against a rule dated 2026-08-31 that says
none may exist at all.

The state machine in `ticket.py` is the strongest thing here. `blocking_reasons` genuinely is one
place, `GateFacts` is an elegant split, and the gates hold. What does not hold is the layer
beneath them: the store, the shell, and the identity of the actor. A gate that asks "has Clyde
checked this?" and accepts `--actor clyde` from the agent that wants past it is not asking a
question.

I did not find dishonesty. I found a codebase that documents its known limits carefully —
`cmd_cso`'s docstring says outright that it "cannot cryptographically tell one subagent from
another" — and then ships newer gates with the same limit undocumented. The habit is there. It is
being applied unevenly.

**On the scope.** It is the right scope but it is missing the part that matters most. Everything
you named is the advisory layer plus the CLI. The *enforcement* layer is
`/home/patrick/projects/claude-env/shared/git-hooks/`, and *activation* lives in
`/home/patrick/.claude/settings.json` — neither was in scope, and both carry findings I could not
have reached otherwise (F2, F13, F16). `main_branch_guard`'s own note says so: "Enforcement is
the git hook; authority is branch protection." Review the layers together or you review the one
that admits it can be spelled around.

## 2. Findings at a glance

| # | Area | Severity | Finding |
|---|------|----------|---------|
| 1 | shared parser | **Bug-Major** | `_shell.py` and `_repo_context.py` are one module written twice; the harness copy never joins line continuations, defeating six gates |
| 2 | zero trust | **Bug-Major** | 25 agent-typable bypass tokens in the live controls; most are printed inside the refusal |
| 3 | `git_commit_guard` | **Bug-Major** | Issues `permissionDecision: "allow"` for anything matching a naive regex, on any branch the agent names |
| 4 | `main_branch_guard` | **Bug-Major** | 4 destructive refusals broken by ordinary spellings; 3 SQL refusals unreachable |
| 5 | interpreter parsing | **Bug-Major** | `bash -lc` defeats every `scannable_text` guard; `bash -cl` defeats every reserved ticket command |
| 6 | gate 4 | **Bug-Major** | The ticket id may sit anywhere in the command — a comment, a path, an `echo` — not in the message |
| 7 | `enforce_subagent_model` | **Bug-Major** | Refuses the documented dispatch of its own allowlisted roles; forces the caller to assert a tier |
| 8 | `ci_cost_guard` | **Bug-Major** | The "permanent" macOS-CI ban resolves the target repo from `cwd` alone; `cd &&` and `git -C` walk past it |
| 9 | `ticket_watch_gate` | **Bug-Major** | Trusts an unsigned heartbeat file with no PID and a future-is-fresh rule |
| 10 | `commit_message_substitution_guard` | **Bug-Major** | `git␣␣commit` (two spaces) and `git⇥commit` bypass a guard whose docstring says it cannot fail open |
| 11 | Clyde gate | Bug-Minor | The `in_review` gate is satisfied by the dev typing `--actor clyde` |
| 12 | `ticket_store_guard` | Latent | A relative `file_path` is never absolutised; the watch heartbeat is outside the guarded shape |
| 13 | bypass corpus | Bug-Minor | The accumulator stopped accumulating: no push family, no `rm`/`clean`/`checkout`/SQL entries |
| 14 | `run-hook-tests.sh` | Bug-Minor | Exits 0 on zero tests, yellow-skips an orphaned hook, and nothing automated runs it |
| 15 | external tools | Latent | `merged_pr_guard` / `pr_after_accept_guard` read a failed lookup as "no violation" |
| 16 | manifest | Bug-Minor | 49 of 82 hooks absent from the public contract; the guard that would block that is unwired |
| 17 | `regression_test_red_verify` | Minor | 8 green tests, wired nowhere, enforcing a convention nothing uses |
| 18 | `blocking_reasons` | Minor | 410 lines; `cmd_uat` filters its verdict by grepping its own English |
| 19 | `ticket_commit_guard` | Bug-Minor | `git log --grep commit` is refused as a commit |
| 20 | `ticket_new_test_file_guard` | Bug-Minor | `conftest.py` is invisible to the freelance-suite gate |
| 21 | misc | Trivial | Duplicate import block; a driver header naming the wrong hook; `pr_state_injector` has no FIRES fixture |

## 3. Detailed findings

### F1. One parser, two repos, and each copy carries the hole the other fixed

**Location:** `plugins/psford-tickets/hooks/_shell.py` `statements()` (26–46) vs
`claude-env/.claude/hooks/_repo_context.py` `statements()` (40–64) · **Bug-Major**

`_shell.py`'s own docstring is about this exact risk: *"the same parsing was written twice and
only one copy was correct… A guard is only as good as its parser. Two parsers means one of them
is wrong and nobody knows which, so there is one here and the guards import it."* There is one
**per repo**, and they are two.

`_repo_context.py` joins backslash-newline continuations before splitting, because not doing so
*"permitted both a commit onto main and a destructive reset past the guards that exist to refuse
them."* That fix never crossed to `_shell.py`:

```
input: 'ticket \\\n  uat CH-1 --verdict accepted'
_shell.statements        -> ['ticket \\', 'uat CH-1 --verdict accepted']
_repo_context.statements -> ['ticket   uat CH-1 --verdict accepted']
```

Consequences, every one run against the live hook:

```
BLOCK  'ticket uat CH-1 --verdict accepted'
allow  'ticket \\\n  uat CH-1 --verdict accepted'      <- Patrick's verdict, forged
allow  'ticket ac \\\n  remove CH-1 --ac AC1'
allow  'rm \\\n  ~/.local/share/harness/claude-harness/tickets/CH-1.json'
allow  'git \\\n  commit -m "wip"'                     <- gate 4, gone
```

The parallel audit reproduced the same bypass against `ticket_pr_guard`, `ticket_ui_uat_guard`,
`ticket_commit_scope_guard` and `ticket_watch_gate`. That is six gates from one missing regex.

The drift runs both ways, so neither file is a superset: `_shell.GIT_INVOCATION` is
`^(?:\S*/)?git\b` and does not allow a leading env assignment or `sudo`, which `_repo_context`'s
does; `_shell.target_directory` handles `--git-dir`, which `_repo_context`'s does not. And
`ticket_commit_guard.py` lines 17–20 carry the instruction that was not followed: *"If a third
copy appears, promote it to claude-env as shared tooling rather than copying again."*

**Mitigation:** make `_shell.py` a thin re-export. Copy `CONTINUATION`, `statements`,
`GIT_INVOCATION`, `strip_heredoc_bodies` and `target_directory` from `_repo_context.py` verbatim,
taking the union of the two `target_directory` flag lists (`-C`, `--git-dir`, `--work-tree`,
`--namespace`). Then add `tests/test_parser_sync.py` asserting the two files' shared function
sources are byte-identical, failing loudly if `../claude-env` is absent — the same "absence, not
drift" contract `shared_rules_link_guard` already implements, and the same shape as the existing
`tests/test_version_sync.py`. A fix landing in one file and not the other is the defect this repo
produces most; a test is the only thing that notices.

### F2. Twenty-five agent-typable bypasses, most of them advertised in the refusal

**Location:** across `claude-env/.claude/hooks/`, `claude-env/shared/git-hooks/`, and
`plugins/psford-tickets/cli/ticket.py` · **Bug-Major**

The shared rule is not ambiguous: *"No hook gets an agent-usable override — no env-var, no magic
comment, no acknowledgement token an agent can type… Proposing a new self-serve hatch is itself a
violation."*

Environment variables and command tokens (7), all in wired hooks: `SHARED_RULES_OK`,
`CWD_DRIFT_OK`, `PARK_OK`, `CI_RUN_OK`, `CI_MACOS_PUSH_OK`, `ENGINES_NODE_OK`, `MANIFEST_EXEMPT`.

Magic comments (13): `AC-DESCOPE-OK`, `API-URL-UNVERIFIED-OK`, `BRANCH-OK`, `DEFER-PERMANENT`,
`DESIGN-SIGNOFF-OK`, `DRIFT-OK`, `EXISTENCE-CHECK-OK`, `INFRA-DEPLOY-OK`, `PARK-OK`,
`PLACEHOLDER-OK`, `SIMPLEST-PATH-OK`, `STALE-PATH-OK`, `STDERR-SUPPRESS`.

Shared git hooks (3): `ALLOW_PROTECTED_COMMIT`, `ALLOW_PROTECTED_PUSH`, and — undocumented,
untested, unmentioned anywhere — `GIT_PROTECTED_BRANCHES`.

Harness CLI (2): `TICKET_PARALLEL_OK` (`ticket.py:4261`), `TICKET_ORPHAN_OK` (`3022`, `3808`),
both labelled "the fixture escape" and both readable from any agent's shell.

Proven against `shared/git-hooks/pre-push` with a real ref list on stdin:

```
refused  plain push to main
ALLOWED  ALLOW_PROTECTED_PUSH set
ALLOWED  GIT_PROTECTED_BRANCHES=nothing
```

Two things make this worse than a list. The refusals **teach the bypass**: `pre-push` ends with
`ALLOW_PROTECTED_PUSH="<reason>" git push ...`; `cwd_drift_guard` ends with *"add CWD_DRIFT_OK to
it"* — it printed that at me during this review; `shared_rules_link_guard.py:184` prints *"Bypass
with SHARED_RULES_OK=1."* And `pre-commit` asserts, four lines above its own hatch, *"there is no
way to phrase the commit that avoids it."*

The honest framing: TNO is dated 2026-08-31 and most of these hooks are older. Nobody audited the
class when the rule landed. The 2026-09-09 postmortem calls a single agent-authored widening High
severity; twenty-five standing ones deserve at least a register.

**Mitigation:** three buckets, in one pass. (a) Delete outright where the guard is cheap to
satisfy — `CWD_DRIFT_OK`, `SHARED_RULES_OK`, `STDERR-SUPPRESS`, `SIMPLEST-PATH-OK`. (b) For the
ones that guard a genuinely-sometimes-correct act (`ALLOW_PROTECTED_COMMIT`, `PARK_OK`,
`INFRA-DEPLOY-OK`), move the switch off the agent's command line to a file only Patrick's
terminal writes — `~/.claude/harness-overrides.json` with a timestamp and a scope, expiring in
minutes, so an agent cannot create it and a stale one cannot linger. (c) `GIT_PROTECTED_BRANCHES`
is a configuration knob that doubles as a silent kill switch: split it, reading the protected set
from a committed file and refusing an environment override. Then strip the bypass syntax out of
every refusal message — a refusal names the way *forward*, not the way *around*.
`mutation_harness_guard.py` and `visual_ac_manual_guard.py` already meet this standard; copy them.

### F3. `git_commit_guard.py` grants permission it has no basis to grant

**Location:** `claude-env/.claude/hooks/git_commit_guard.py` `is_feature_branch()` (37–43),
`main()` (68–82) · **Bug-Major**

`is_feature_branch` returns `True` for any branch that is not `develop`, `main`, `master` or
`HEAD`. On such a branch the hook emits `permissionDecision: "allow"` — an active grant that
suppresses the permission prompt, not a passive exit 0. The trigger is
`re.search(r'\bgit\b.*\bcommit\b', command)`.

```
on develop  ask      <- git commit -m x
on develop  ask      <- git checkout -b fix/commit-gate
on develop  ask      <- git log --grep commit
on develop  ask      <- echo "remember to git commit later"

on feat/x   allow    <- git commit -m x
on feat/x   allow    <- git checkout -b fix/commit-gate
on feat/x   allow    <- git log --grep commit
on feat/x   allow    <- echo "remember to git commit later"
```

It grants permission for commands it has not identified, keyed on a branch name the agent chose.
My own review session tripped its `ask` branch on a read-only `for` loop that merely quoted the
words.

The file imports `_repo_context` already (line 25) for two other helpers. `commit_tokens()` sits
in that module and exists precisely to replace this regex — its docstring names the bug: *"On
2026-08-08 exactly that pattern blocked the creation of a branch whose name contained 'commit'."*

Two hooks now issue conflicting permission decisions for the same event: this one and
`gate_git_commit.py`, both wired globally on `PreToolUse`/`Bash`. Nothing in either repo
establishes which prevails, and no test asserts the pair's combined behaviour. I could not
determine the combination semantics from here and I am not going to guess.

**Mitigation:** delete `git_commit_guard.py`. Its job is a strict subset of `gate_git_commit.py`,
which does it correctly with a real ticket-in-progress exemption via `_repo_context.ticket_store()`.
If it must stay, replace line 68 with `if commit_tokens(command) is None: return 0` and replace
the `allow` with a silent `return 0` — a hook that cannot verify the protocol was followed must
abstain, never grant. Then add a test asserting exactly one hook returns a `permissionDecision`
for a commit payload.

### F4. `main_branch_guard`'s destructive block is broken in four spellings, and its SQL block is unreachable

**Location:** `claude-env/.claude/hooks/main_branch_guard.py` lines 183–237, `forced_push()`
(78–90) · **Bug-Major**

```
BLOCK  rm -rf /tmp/zzz                       allow  rm -fr /tmp/zzz
allow  rm -r -f /tmp/zzz                     allow  rm --recursive --force /tmp/zzz
BLOCK  git checkout .                        allow  git checkout . && ls
allow  git checkout .; ls                    allow  git restore --staged --worktree .
BLOCK  git push --force origin dev           allow  git push origin +dev:dev
BLOCK  DROP TABLE users                      allow  psql -c "DROP TABLE users"
allow  sqlcmd -Q "DROP TABLE users"          allow  mysql -e "TRUNCATE TABLE users"
allow  psql <<'SQL' DROP TABLE users; SQL    allow  az sql db query --query "DROP DATABASE prod"
```

Four distinct causes, four distinct fixes:

- `r'\brm\b\s+.*-[a-zA-Z]*r[a-zA-Z]*f'` (206) demands `r` before `f` in one cluster. `rm -fr` is
  the second-most-common spelling of the command this guard exists to stop.
- `\s*$` on lines 189 and 195 anchors to the end of the whole scannable text, which joins
  statements with newlines — so any compound command escapes. `git restore --staged --worktree .`
  fails for a second reason: the regex requires `.` immediately after `restore`.
- `forced_push()` reads flags only. A leading `+` on a refspec is the original force-push
  spelling and it is invisible here, while the message says *"force-pushing is forbidden on any
  branch."*
- The SQL block is dead. `scannable_text` blanks quoted arguments and only exempts a fixed
  `INTERPRETERS` list, so every realistic way of sending SQL is invisible. The only input that
  trips it is a bare `DROP TABLE users` typed as a shell command, which is not a runnable command
  at all.

The reason none of this was caught: all 35 fixtures in `tests/main_branch_guard/` are about push
refspecs, force flags, branch resolution, and prose-versus-command. Not one exercises the
destructive block. The bypass corpus covers `reset --hard` and `gh pr merge` and contains **zero**
entries matching `rm`, `clean`, `checkout`, `restore`, `DROP`, `TRUNCATE` or `DELETE`. Six of
eleven refusal branches have no coverage in either place, and I proved four of them broken.

**Mitigation:** move the destructive checks off regexes and onto tokens, per statement. Iterate
`statements(scannable)` rather than searching the joined text, which fixes the `$`-anchor class at
a stroke. For `rm`, tokenise and refuse when any argument is a short-flag cluster containing both
`r` and `f`, or when `--recursive` and `--force` both appear. For `restore`/`checkout`, refuse
when `.` appears among the positional arguments regardless of preceding flags. Add `+` refspec
detection to `forced_push()`. For SQL, stop trying to read it out of a quoted argument — the
honest move is to delete those three branches and say so, or to add `psql`, `sqlcmd`, `mysql`,
`sqlite3` and `az sql` to a second list whose `-c`/`-Q`/`-e`/`--query` argument is scanned whole.
Then add one fixture per branch and one corpus entry per spelling above.

### F5. `bash -lc` and `bash -cl` — two sibling parsers, two opposite one-character bugs

**Location:** `_repo_context.scannable_text()` (160–161) and `ticket_bash_guard.shell_payload()`
(468–475) · **Bug-Major**

`scannable_text` exempts an interpreter statement only when `"-c" in tokens or "-e" in tokens` —
an exact token match, so a combined flag defeats it:

```
                            plain    sh -c    bash -lc
main_branch_guard           BLOCK    BLOCK    allow     git reset --hard HEAD~1
main_branch_guard           BLOCK    BLOCK    allow     gh pr merge 17
```

`git reset --hard` is the command the rules single out as having destroyed work, and no git hook
exists that could catch it downstream. There is no second layer here.

The harness's `shell_payload` has the opposite bug. It tests `token.endswith("c")`, which catches
`-lc` and misses `-cl`:

```
BLOCK  bash -lc 'ticket uat CH-1 --verdict accepted'
allow  bash -cl 'ticket uat CH-1 --verdict accepted'
allow  bash -cl 'ticket answer CH-1 --answer yes'
allow  bash -cl 'ticket reopen CH-1 --note x'
allow  bash -cl 'ticket ac remove CH-1 --ac AC1'
allow  bash -cl 'ticket set CH-1 --requires-uat false'

bash -cl 'echo RAN'  ->  rc=0, out='RAN'
```

Every reserved command in the system falls to a letter swap. `cmd_uat` in `ticket.py` has no
actor check of its own, so `ticket_bash_guard` is the only thing standing between an agent and a
forged UAT verdict.

**Mitigation:** one predicate, in the shared parser, used by both. A shell's command flag is any
single-dash cluster containing `c`: `re.fullmatch(r'-[A-Za-z]*c[A-Za-z]*', token)`. In
`scannable_text`, replace the `"-c" in tokens` test with that predicate applied across tokens
(keeping the `-e` case for perl/ruby). In `shell_payload`, replace `token.endswith("c")` with the
same, and skip a value for `--rcfile`/`--init-file`. Then add both spellings to the bypass corpus,
in a new `interpreter_wrapper` family.

### F6. Gate 4 accepts the ticket id anywhere in the command, not in the message

**Location:** `ticket_commit_guard.py` `message_text()` (285), `main()` (449) · **Bug-Major**

`message_text` begins `text = command` — the whole raw command string — and the id regex is
applied to that. Run against the live board (`CH-234` in progress):

```
BLOCK  no ticket named                    'git commit -m "wip"'
allow  id in a shell COMMENT              'git commit -m "wip"   # CH-234'
allow  id in a path                       'cd /tmp/CH-234 && git commit -m "wip"'
allow  id in an unrelated echo            'echo CH-234 >/dev/null && git commit -m "wip"'
allow  id in --author                     'git commit -m "wip" --author="CH-234 <a@b.c>"'
```

In every allowed case the commit lands with no ticket in its message. The docstring's premise —
*"The ticket ID in a commit message is the join between workflow state and version control.
Without it the store drifts into fiction"* — describes a gate that does not exist. Ironically the
sibling exemption `only_touches_the_ticket_store` gets this exactly right and says why: *"It reads
paths, never the message… a marker anyone can type is a bypass rather than an exemption."* The id
check is the marker anyone can type. None of the 221 tests in `tests/test_hooks.py` distinguishes
the two.

**Mitigation:** build the message from the message, not the command. Collect the values of every
`-m`/`--message` token, the contents of any `-F <path>`, and — only when `-F -` or `--file -` is
present — the heredoc body. Search that text for ids. `shlex` has already tokenised the statement
in `is_commit`, so the values are in hand. Add a fixture for each of the four allowed rows above.

### F7. The model-tier guard refuses the documented dispatch of its own allowlisted roles

**Location:** `enforce_subagent_model.py` `main()` (61–87) · **Bug-Major**

The hook reads `tool_input["model"]` — the caller's *override* — and denies when it is absent. But
the agent definitions already declare the tier: `agents/grace.md` says `model: opus`,
`agents/clyde.md` says `model: haiku`. So the correct dispatch, naming the role and letting the
definition decide, is refused. Proven on my own first call in this review:

> `BLOCKED: subagent model must be sonnet or haiku (got: unset).`

`skills/implementing-a-story/SKILL.md` line 169 tells the dev `<dispatch the Clyde check>` and
never mentions a model, because the definition supplies it. A dev following that skill literally
is blocked, and the refusal's own advice — *"Re-issue with model: 'sonnet'"* — runs Clyde at four
times its intended tier with nothing recording the discrepancy.

The file 200 lines away in `ticket.py` contains the principle this violates. `DISPATCH_TIER_ENV`'s
comment (55–64): *"a flag is something the agent types and an agent cannot know this. Ask a model
which model it is and you get a fluent answer with no observation behind it."* This hook has made
the typed assertion mandatory. And it makes the frontmatter decorative: the caller's value always
wins, so the per-role tier pinning that the definitions exist to provide is displaced by the
assertion the guard was built to distrust.

`tests/test_hooks.py:2536`, `test_ac10_unset_model_denies`, locks the defect in.

**Mitigation:** when `model` is absent, resolve the definition and judge that. Read
`os.path.join(os.path.dirname(__file__), "..", "agents", f"{_role(subagent_type)}.md")`, parse the
`model:` line, and apply the existing rules to it. Deny when the file is missing or unreadable —
default-closed is preserved, it just now closes against the right fact. Replace `test_ac10` with
two tests: unset model + allowlisted role whose definition says opus **allows**; unset model with
no resolvable definition **denies**.

### F8. The "permanent" macOS-CI ban is bypassed by two ordinary ways of naming another repo

**Location:** `ci_cost_guard.py` `_repo_root()` (110) and its callers · **Bug-Major**

The guard resolves the target repository from the payload's raw `cwd` and nothing else. Against a
scratch repo carrying a real `runs-on: macos-latest` workflow on `push`:

```
BLOCK  push, cwd = the macOS repo
allow  same push via git -C, cwd elsewhere
allow  same push after cd
BLOCK  dispatch, cwd = the macOS repo
BLOCK  dispatch by --repo, cwd elsewhere
BLOCK  gh api .../dispatches, cwd elsewhere
```

(The `gh` half is sound — I could not reproduce the wider claim my audit made about it.) But the
git-push half is real, and `cd /path/to/repo && git push` is how most pushes in this workspace are
actually written. The docstring says *"UNCONDITIONAL BLOCK. No bypass token exists on purpose —
this is the permanent iOS-on-GitHub ban."* Patrick's own note prices macOS runners at 10× — this
is a money control.

**Mitigation:** one line. `_repo_context.target_directory(command, default=payload_cwd)` already
handles `cd` and `git -C` correctly and lives in the same directory. Replace the bare `cwd` with
that call. Add two fixtures: the same push spelled `cd X && git push` and `git -C X push`, both
BLOCK.

### F9. The watch gate trusts a file anyone can write

**Location:** `ticket_watch_gate.py` `main()` (104–116) · **Bug-Major**

The gate refuses board writes unless a heartbeat at
`<data home>/harness/ticket-watch.heartbeat.json` is fresh. The heartbeat is `{at, roots, stores}`
— no PID, no signature, nothing tying it to a running process — and line 24 makes a future-dated
`at` count as fresh, deliberately, for clock skew. So `{"at": 9999999999}` is permanently fresh.

That file is also outside `ticket_store_guard`'s guarded shape
(`harness/<repo>/tickets/*.json`), which I confirmed directly:

```
absolute store path       -> BLOCK
watch heartbeat file      -> allow
```

One `Write` to a path the refusal message itself names disables the gate for the rest of the
session. The docstring's claim — *"What a hook CAN do is make an unarmed session unable to write
to the board"* — is false; the session is unable only until it writes three lines of JSON.

**Mitigation:** two changes, both small. Have `bin/ticket-watch.py` stamp `"pid": os.getpid()`
into each heartbeat, and have the gate verify that `/proc/<pid>/cmdline` contains
`ticket-watch.py` before trusting the timestamp — liveness checked against the process table, not
against a number in a file. Separately, drop the future-is-fresh rule: clamp `age` to
`max(0, now - at)` and refuse a heartbeat dated more than a tick ahead.

### F10. `commit_message_substitution_guard` fails open on whitespace, in the one file that says it cannot

**Location:** `commit_message_substitution_guard.py` line 65 · **Bug-Major**

```python
if "git commit" not in command: return 0
```

A literal substring with exactly one space:

```
rc=2  'git commit -m "pwned: $(whoami)"'
rc=0  'git  commit -m "pwned: $(whoami)"'
rc=0  'git\tcommit -m "pwned: $(whoami)"'
```

All three are identical to bash and all three execute the same `$(whoami)` substitution before git
sees the message. The file's docstring (35–36) explains that it is a regex scan rather than a
parser precisely because *"a parser that got this wrong would fail open, and the whole point is
that this cannot fail open."* Line 65 is that failure, in the guard rail built to prevent it.

**Mitigation:** `if commit_tokens(command) is None: return 0`, importing from `_repo_context` as
the neighbouring hooks do. Failing that, `re.search(r'\bgit\s+commit\b', command)`. Add both
whitespace variants as fixtures.

### F11. The Clyde gate is satisfied by the dev typing `--actor clyde`

**Location:** `ticket.py` `blocking_reasons` `target == "in_review"` (2336–2356), `cmd_evidence()`
(4653–4692), parser at 5783 · **Bug-Minor**

The newest gate in the state machine requires a passing `actor == "clyde"` evidence entry per
automated criterion. `--actor` is `choices=ROLES, default="dev"` — free text from the caller.
Nothing verifies a Clyde subagent ran; no hook in `hooks/` mentions clyde at all; the plugin
registers no `PostToolUse` handler that could observe one. The dev agent that wants past the gate
can write the evidence that opens it.

This is a known limitation elsewhere and documented there. `cmd_cso` (3238) says plainly: *"This
refuses the wrong VALUE and stamps the record `actor: "cso"`, but it cannot cryptographically tell
one subagent from another… a hook that blocks this command outside a real CSO context is possible
future hardening."* The Clyde gate has the identical limit and says nothing, and its gate comment
reads as though a recorded check is a fact.

**Mitigation:** the mechanism already exists one field over. Add a `PostToolUse`/`Agent` hook
that, when `subagent_type` resolves to `clyde`, writes a short-lived token to
`<data home>/harness/<repo>/clyde-runs/<ticket>-<ac>.json`; have `cmd_evidence` refuse
`--actor clyde` unless a matching unconsumed token exists, and consume it. That is the same "the
party that knows is the party that dispatched" reasoning `DISPATCH_TIER_ENV` already uses. Until
that ships, add the CSO paragraph verbatim to `cmd_evidence`'s docstring — a documented limit is a
different thing from an invisible one.

### F12. `ticket_store_guard` never absolutises a relative path

**Location:** `ticket_store_guard.py` `guarded()` (49–60), `main()` (104) · **Latent**

```
absolute store path       -> BLOCK
relative, cwd = the store -> allow
./relative, cwd = store   -> allow
```

`NEW_STORE_RE` requires `(^|/)harness/<x>/tickets/<y>.json`. A relative `file_path` matches neither
regex and falls to `return False`. `cwd` is passed in but reaches only the *legacy* branch. The
docstring says *"Fails closed by construction… Anything it cannot answer stays guarded"*; the
comment at 105–108 says *"Only relative paths depend on it, and those are exactly the ones an
agent writes."* Neither is true of the new-store shape.

Rated Latent rather than Major because the Write and Edit tools currently require absolute paths,
which masks it. That is a property of the tool layer, not of this hook, and not one the hook
should depend on — the matcher includes `MultiEdit` and `NotebookEdit`, and any future or
MCP-provided writer is outside that guarantee.

**Mitigation:**

```python
cwd = data.get("cwd") or os.getcwd()
abs_path = path if os.path.isabs(path) else os.path.join(cwd, path)
normalised = os.path.normpath(abs_path).replace(os.sep, "/")
```

and extend the guarded shape to cover bare files directly under `harness/`, which closes the
heartbeat route in F9 as defence in depth.

### F13. The bypass corpus stopped accumulating

**Location:** `claude-env/shared/bypass-corpus.json` (25 entries) · **Bug-Minor**

The corpus is the best idea in either repo — its docstring diagnoses the failure exactly: *"an
evasion was thought of only after it had already been used, a test was added for that one form,
and nothing accumulated. This is the accumulator."* It then stopped. Families present:
`commit_on_main`, `destructive`, `false_positive`, `conservative_block`. There is **no push family
at all**, so the pre-push hook — the enforcement layer for the rule that matters most — has no
corpus coverage, and neither of its bypasses is recorded as a known hole. The `destructive` family
contains five entries, all `reset --hard` or `gh pr merge`. A grep across all 25 entries for `rm`,
`clean`, `checkout`, `restore`, `DROP`, `TRUNCATE` or `DELETE` returns nothing.

**Mitigation:** add a `push_to_main` family with the refspec spellings `test_git_hooks.py` already
exercises, plus `ALLOW_PROTECTED_PUSH` and `GIT_PROTECTED_BRANCHES=nothing` recorded honestly as
`stopped_by: "none"` while they exist — the corpus's own contract is that a hole is documented
rather than surprising. Add the destructive spellings from F4 and the wrapper spellings from F5.
Then make it a rule: every fix in F1–F10 lands a corpus entry.

### F14. The runner reports success when it finds nothing, and nothing runs it

**Location:** `run-hook-tests.sh` lines 52, 135–137 · **Bug-Minor**

```
$ bash .claude/hooks/tests/run-hook-tests.sh gate_git_commit
NO HOOK TESTS FOUND
EXIT=0
```

`gate_git_commit` exists and is wired globally. A filter naming a hook with no tests — or a typo —
is a green run. Line 52 does the same for the reverse case: a test directory whose hook has been
renamed prints a yellow `[skip]` and is not counted as a failure. The file's own comments call
this out for fixture filenames — *"a typo silently reducing coverage, which is the same 'skipping
X' mask this repo keeps finding"* — and then leave the mask in the two branches above.

Compounding it: `grep -r run-hook-tests` finds no CI workflow, no entry in
`shared/git-hooks/pre-commit`, no pre-push. The safety net for 82 controls runs only when a human
types it.

**Mitigation:** make `total -eq 0` exit 1 with `NO HOOK TESTS FOUND — this is a failure, not a
pass`. Make the missing-hook branch at line 52 a counted failure. Add a wiring assertion — a test
that reads both settings files and the unwired register in
`docs/reviews/2026-08-10-unwired-guards.md` and fails when a hook is in neither, which is the
pattern `tests/test_hooks.py::TestSubagentModelHookWiring` already implements in the harness. Then
run the suite from `shared/git-hooks/pre-commit` when anything under `.claude/hooks/` is staged.

### F15. Two guards read a failed lookup as "no violation"

**Location:** `merged_pr_guard.py` `check_pr_state()` / `check_current_branch_pr()` (22–48);
`pr_after_accept_guard.py` `ticket_state()` (72–93), `main()` (126) · **Latent**

Both wrap their subprocess call in a bare `except` returning `None`, and both callers treat `None`
as clean — `if state and state in ("MERGED","CLOSED")` and `if st is None or st == "accepted":
continue`. Any `gh` or `ticket` failure (binary absent, auth expired, rate limit, timeout,
malformed JSON) is a silent full pass. `pr_after_accept_guard`'s docstring says *"There is NO
override"*; operationally, a transient tool failure is one.

I could not construct a differential reproduction from my worktree — my scratch repos have no PR
and no matching ticket, so both paths return 0 for legitimate reasons. The defect is code-evident
at the line numbers above, and my audit reported a clean differential using stub binaries. I am
stating it at the confidence I actually have.

**Mitigation:** distinguish "the tool answered and there is nothing to report" from "the tool could
not be consulted." Return a sentinel for the latter and refuse on it, with a message naming the
failure. `gate_git_commit.py` already does this correctly — its fallback is `ask`, not `allow`.
Note the deliberate counter-example in `ticket.py`'s `path_is_tracked` (1193–1234), which fails
*open* and explains why: *"That guard is stopping something bad from getting in; this one is
stopping someone from moving their own ticket forward."* That reasoning is right, and it does not
apply to either of these two.

### F16. Forty-nine of eighty-two hooks are missing from the public contract

**Location:** `tooling-manifest.json` (70 `tools[]` entries), `manifest_completeness_guard.py` ·
**Bug-Minor**

CLAUDE.md calls this file a public contract consumed by `claude-mac-env`'s bootstrap, and says
`manifest_completeness_guard.py` *"BLOCKS commits that add files under `.claude/hooks/` … without
a corresponding `tools[]` entry."* It blocks nothing: it appears in no settings file and in no git
hook. Result: 49 of 82 hooks have no entry, including live ones — `agent_worktree_default_guard`,
`merged_pr_guard`, `stderr_suppression_guard`, `pr_state_injector`, `cross_repo_fix_audit`. (Zero
stale entries in the other direction, which is worth saying.) A downstream user tiering by this
manifest gets 40% of the tooling.

**Mitigation:** wire `manifest_completeness_guard.py` into `shared/git-hooks/pre-commit`, where
CLAUDE.md already claims it runs, and delete its `MANIFEST_EXEMPT` hatch per F2. Then run
`manifest_classification_guard.py` over the 49 and land the proposed entries in one commit.

### F17. A guard with eight green tests that has never run

**Location:** `regression_test_red_verify.py` and its 8 fixtures · **Minor**

This is the cleanest instance of the shape you asked me to hunt. Eight fixtures pass on every run
and count toward `ALL 200 HOOK TESTS PASSED`. The hook is referenced by nothing but its own test
driver, two docs and `claudeLog.md`. It is not in `docs/reviews/2026-08-10-unwired-guards.md`
either, so it is in neither state — it reads as coverage. And the `RED: <sha>` convention it
enforces appears nowhere in the current skills: `grep -rn "RED:" plugins/psford-tickets/skills/`
returns nothing. It is enforcing a superseded process.

**Mitigation:** decide, and record the decision. Either wire it to the convention now in use —
`judging-test-sufficiency` still requires a bug fix's regression test to be verified red — or move
it into the unwired register with the others. Whichever way, the runner change in F14 should mark
tests for an unwired hook distinctly, so eight green ticks never again stand for a control nobody
is running.

### F18. `blocking_reasons` is 410 lines, and `cmd_uat` filters its own verdict by grepping English

**Location:** `ticket.py` `blocking_reasons` (2131–2541), `cmd_uat` (5274) · **Minor / Latent**

The file is 5,935 lines, 141 top-level definitions, 27 subcommands, 40% prose. `blocking_reasons`
is the longest thing in it, and it tells you so itself at 2419–2422: a redundant
`target == "accepted"` condition is *"kept because this condition is 200 lines from that `if` and
reads wrong without it."* A clause kept alive to compensate for a function's length is the function
reporting its own defect.

Separately, at line 5274:

```python
reasons = [r for r in blocking_reasons({**t, "status": "in_review"}, "accepted", root)
           if "UAT" not in r]
```

A gate decision filtered by substring-matching its own English. Any future refusal whose prose
happens to contain "UAT" is silently dropped, and nothing would notice. This is the one place in
the file where a decision is made by reading a message rather than a value.

**Mitigation:** split `blocking_reasons` by target — `_reasons_for_ready`,
`_reasons_for_in_progress`, `_reasons_for_in_review`, `_reasons_for_accepted` — dispatched from a
table, keeping `blocking_reasons` itself as the public entry point so all 964 test call sites are
untouched. `GateFacts` already isolates the disk. Hoist the four exemption booleans into one
`exemptions(ticket)` helper. For `cmd_uat`, give reasons a structured form — `(code, text)` pairs,
or a `skip={"uat"}` parameter — so the filter tests a value, and delete the substring match.

### F19–F21. Smaller things, with fixes

**F19.** `ticket_commit_guard.is_commit` uses `"commit" in tokens` (86), so `git log --grep commit`
is refused as an unnamed commit (proven: BLOCK). Use `_repo_context.commit_tokens()`. *Bug-Minor.*

**F20.** `ticket_new_test_file_guard.is_test_convention_path()` (45–50) does not recognise
`conftest.py` — a root `conftest.py` is exactly the shared test infrastructure the guard's
docstring exists to refuse, and it is allowed. Add
`if os.path.basename(rel_path) == "conftest.py": return True`. *Bug-Minor.*

**F21.** Three trivia. `ticket_bash_guard.py` carries the same `sys.path.insert` + `import ticket
as cli` block twice at 38–41 and 156–159 — delete the second. `tests/ci_cost_guard/_invoke.sh`'s
header reads `# Driver for park_before_toss_guard.py tests.` `tests/pr_state_injector/` holds three
SILENT fixtures and no FIRES fixture, so the hook's entire reporting branch is untested.
*Trivial / Bug-Minor.*

## 4. Strengths

I want to be specific here, because the list of findings is long and it would be easy to read this
as a bad codebase. It is not.

**`_repo_context.py` is excellent** — the right abstraction, found the right way. One module
answers "which repository is this about", 28 hooks were fixed without rewriting their internals,
and every design choice carries the incident that forced it. The bug is that a second copy exists,
not that this one is wrong.

**The fixture drivers are genuinely rigorous, and I verified it rather than assuming it.** I
neutered four hooks and re-ran their fixtures: `main_branch_guard` 18 of 18 BLOCK fixtures failed,
`ci_cost_guard` 9 of 9, `park_before_toss_guard` 3 of 3, `merged_pr_guard` 2 of 2. A parallel pass
extended that to all 32 hooks with BLOCK/FIRES fixtures — none survived — and ran the inverse
mutation, forcing each hook to always-block and checking the PASS/SILENT fixtures caught it. They
did. `_advisory_driver.sh` requiring `EXPECT_MATCH` on every FIRES fixture, because "produced some
output" once let a wrong `--actor` ship, is the kind of detail most suites never reach.

So the honest answer to your central question is a split one: **the suite would notice a guard
that stopped working. It would not notice one that never worked for a spelling nobody wrote a
fixture for** — which is exactly what F4 and F5 are, sitting under 35 green ticks.

**`test_bypass_corpus.py` is the best idea in either repo.** Asserting that the *record* of which
layer stops each form is still true — including asserting that forms recorded as unstopped really
are still unstopped, so the corpus cannot go quietly stale in the flattering direction — is a
genuinely original piece of test design. My criticism in F13 is only that it stopped growing.

**`shared/git-hooks/pre-push` has the right architecture.** Reading the refs git resolved instead
of the command line is the correct answer to the CH-8 arms race, and the comment explaining why
`--git-path` would cause unbounded recursion is the kind of thing that saves the next person three
hours. The hatch is a policy problem, not an engineering one.

**`GateFacts` is elegant.** Lazy because `load_host` raises; `KeyError` on an unsupplied key
because a stub answering `None` is a gate passing for the wrong reason. Both choices are exactly
right and both are explained.

**The unwired-guards register** is unusually honest engineering: 28 hooks wired to an interpreter
that did not exist, unwired rather than quietly activated, with every rule they encoded written
down so it survives the enforcement. Most teams would have deleted the files and said nothing.

**Refusals name a way forward.** `enforce_subagent_model` blocked me and told me precisely how to
proceed; I was unblocked in one turn. That is the standard, and nearly every guard here meets it.
It is also why F2 stings: the same instinct, applied one step too far, turned "here is the way
forward" into "here is the way around."

**`ticket.py`'s comments.** Forty per cent prose, and it is the good kind — every paragraph names a
date, an incident, and what it cost. `cmd_cso` volunteering that it "cannot cryptographically tell
one subagent from another" is a codebase telling the truth about itself. F11 exists because that
habit was not applied to the newest gate, not because the habit is missing.

## 5. Recommended order

**First, F1 — the parser.** Not because it is the worst but because six other findings are
downstream of it, and fixing it once fixes them everywhere. Land the parser plus the identity test
before touching any individual guard, or you will fix the same bug six times and miss the seventh.

**Second, F5 and F10 — the one-line parser bugs.** Both are single-predicate changes on top of
F1's work, both defeat the highest-value controls in each repo (`git reset --hard`; the UAT
verdict), and both are cheap enough to land in the same session.

**Third, F2 — the bypass audit.** Before any of the remaining guard fixes, because it determines
what "fixed" means. There is no point hardening `main_branch_guard`'s `rm` handling while a magic
comment walks past the result. This one needs Patrick's decision, not just an engineer's, so start
it early and let it run in parallel.

**Fourth, F3, F6, F8, F9 — the four gates that are not gates.** Each is independent and each is
small. Take F3 first (deleting a file is the cheapest fix in this review), then F8 (one line), then
F6 and F9.

**Fifth, F13 and F14 — the safety net.** Deliberately after the fixes rather than before: every fix
above should land its corpus entry and its fixture, and you want the runner honest and running
automatically by the time that work is done, so nothing regresses quietly. F14's wiring assertion
also resolves F17 and F16 as a side effect.

**Last, F11, F12, F15, F18–F21.** Real, none urgent. F18's split is the one I would not defer
indefinitely — every gate added to that function makes the next one harder to place, and the file
has already started keeping redundant code to stay readable.

One thing I would not do: treat F4's SQL branches as a fix. Three refusals that no realistic
invocation can reach are not protecting a database; they are three lines that make the file look
like it does. Either wire them to how SQL is actually sent, or delete them and say in the docstring
that database safety is not this guard's job. A control that cannot fire is worse than an absent
one, because someone counts on it.
