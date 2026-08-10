# Hook inventory — claude-env

**Date:** 2026-08-09 · **Ticket:** CH-46 · stage 2 of the CH-36 remediation

The review found 75 hooks, 60 untested. Testing them all is weeks; deciding
which matter is a day. This table exists so that decision can be made without
reading 75 files.

**Nothing here has been deleted.** Deleting a guard is the kind of change whose
cost shows up later and quietly — the thing it guarded against comes back and
nobody notices. The agent proposes; Patrick disposes.

`technique` is from the CH-36 finding that a guard reading command *text* is
advisory at best, while one asking git for *state* is enforcement.

## Fires nowhere — 13

Referenced in no settings file. Not running, not able to run.

| hook | last touched | loc | fixtures | technique | what it guards |
|---|---|---|---|---|---|
| `regression_test_red_verify` | 2026-06 | 271 | **8** | state | regression_test_red_verify.py — pre-push verification of `RED: <sha>` claims. For each commit being pushed who |
| `feasibility_spike_guard` | 2026-06 | 114 | **4** | text | feasibility / spike gate for design & implementation plans. Background: 2026-06-26 single-screen overview. The |
| `plan_descope_drift_guard` | 2026-06 | 114 | **3** | text | plan / decisions.md descope-drift guard. Background: 2026-06-26. When ACs were descoped mid-implementation, th |
| `simplest_path_guard` | 2026-06 | 116 | **3** | text | simplest-path annotation guard for implementation phases. Background: 2026-06-26. A CSS-level task ("make one  |
| `branch_churn_guard` | 2026-06 | 105 | — | text | branch churn / thrash advisory (NEVER blocks). Background: 2026-06-26. Approaches tried-then-abandoned within  |
| `ef_migration_guard` | 2026-03 | 90 | — | text | Enforce EF Core migrations over raw SQL. Enforces rule: - Database schema changes must use EF Core migrations, |
| `js_test_theater_guard` | 2026-08 | 158 | — | text+state | JavaScript test theater guard. Fires on git commit. Detects new .test.js files that define functions at the to |
| `manifest_classification_guard` | 2026-04 | 336 | — | state | Manifest classification commit hook for claude-env. Detects new/changed files in .claude/hooks/ or helpers/ th |
| `plan_phase_count_guard` | 2026-08 | 149 | — | text+state | Implementation plan phase-count guard. Fires on git commit. Detects when a new implementation plan directory a |
| `playwright_gate` | 2026-08 | 137 | — | text+state | block git commit when UI source files are staged without recent Playwright verification. Rules: - Triggers on  |
| `retro_trigger_guard` | 2026-03 | 143 | — | text+state | Retrospective trigger. Fires after git commit. Detects two signals that indicate a retrospective entry should  |
| `session_checkpoint` | 2026-08 | 170 | — | other | Session checkpoint: writes sessionState.md with git state. Triggered by the Stop hook event after every Claude |
| `stale_path_guard` | 2026-03 | 198 | — | text+state | Stale path guard. Fires on git commit. Reads staged diff and blocks (exit 2) if any added line in scanned file |

## Wired, untested, predates this harness — 24

Running with no test, last touched before August.

| hook | wired in | last touched | technique | what it guards |
|---|---|---|---|---|
| `absolute_path_link_guard` | /home/patrick | 2026-06 | other | block assistant replies containing markdown links to RELATIVE paths. Patrick's IDE renders markdown links rela |
| `ac_staleness_guard` | claude-env, claudeProjects | 2026-03 | text | Advisory Claude Code hook (PostToolUse on Bash). When a git push command is detected, checks ac-status.json fo |
| `artifact_path_guard` | claude-env, claudeProjects | 2026-03 | other | Artifact path registry guard. Fires on Write/Edit. Checks the target path against the canonical artifact regis |
| `assert_verify_guard` | claude-env, claudeProjects | 2026-03 | text | Assert-without-verify guard. Fires on Write/Edit to artifact files and Bash commands with hardcoded Azure reso |
| `browser_compat_guard` | claude-env | 2026-04 | text+state | Browser compatibility guard. Fires on git commit. When staged wwwroot/js/*.js files contain Node.js-only APIs, |
| `commit_claim_verify_guard` | claude-env | 2026-04 | text | Commit claim verification guard. Advisory hook (exit 0 with additionalContext — never blocks). When a git comm |
| `constant_change_test_guard` | claude-env | 2026-03 | text+state | Constant change test guard. Blocks commit when a C# numeric constant changes but the test file isn't staged. E |
| `deploy_guard` | /home/patrick, claude-env, claudeProjects | 2026-03 | text | Guard deployment operations. Enforces CLAUDE.md rules: - NEVER deploy without Patrick saying "deploy" - Must c |
| `deprecation_guard` | /home/patrick, claude-env, claudeProjects | 2026-03 | text | Flag deprecated API usage after dotnet builds. After any `dotnet build` command, scans the build output for de |
| `engines_node_guard` | claude-env | 2026-06 | text | Block `npm install` in Node projects that have no version pinning. Background: Node version drift between loca |
| `fix_commit_smell_guard` | claude-env, claudeProjects | 2026-03 | text+state | Fix-commit smell detector. Fires after git commit. If the commit message starts with "fix:" and the committed  |
| `js_coordinate_truthiness_guard` | claude-env | 2026-04 | text+state | JS coordinate truthiness guard. Fires on git commit. Blocks when staged wwwroot/js/*.js files use truthiness c |
| `js_dead_assignment_guard` | claude-env | 2026-04 | text+state | JavaScript dead assignment guard. Fires on git commit. Scans staged wwwroot/js/*.js files for patterns where t |
| `js_module_coverage_guard` | claude-env | 2026-03 | text+state | JS module coverage guard. Blocks commit of new JS source modules >50 LOC without test coverage. Exit code 2 =  |
| `library_intro_guard` | claude-env | 2026-03 | other | Library introduction research gate. Blocks Write of HTML/csproj that adds a new CDN script or NuGet package wi |
| `manifest_completeness_guard` | claude-env | 2026-06 | text | Block commits that add or rename a hook / helper file without a corresponding entry in tooling-manifest.json.  |
| `plan_branch_guard` | claude-env | 2026-06 | text | Block phase plan commits that hardcode already-merged or non-existent branch names. Background: phase plans fr |
| `pr_migration_checklist` | claude-env | 2026-04 | text+state | PR migration checklist. Fires on `gh pr create`. When the diff between current branch and main includes new EF |
| `prod_target_verify_guard` | claude-env | 2026-04 | text | Production target verification guard. Fires on Bash tool. When a command contains 'dotnet' AND sets WSL_SQL_CO |
| `retro_area_overlap_guard` | claude-env | 2026-04 | other | Retrospective area overlap guard. Fires on Write tool. When a NEW source file (does not exist on disk) is bein |
| `session_start` | /home/patrick, claude-env, claudeProjects | 2026-04 | other | Load critical context at session start. Outputs checkpoint reminders, open retro mitigations, and claudeLog st |
| `shellcheck_write_guard` | claude-env, claudeProjects | 2026-03 | other | Bash syntax guard for .sh file writes. Fires on Write tool targeting .sh files. Runs `bash -n` on the content  |
| `spec_staleness_guard` | claude-env, claudeProjects | 2026-04 | text+state | Spec staleness guard. Fires after git push. Compares source-code delta on this branch against the project's te |
| `stderr_suppression_guard` | claude-env, claudeProjects | 2026-03 | text | stderr suppression guard. Blocks Bash commands that redirect stderr to /dev/null on substantive commands (wsl, |

## Wired, untested, actively maintained — 27

Touched this month; running; no test.

| hook | wired in | last touched | technique | what it guards |
|---|---|---|---|---|
| `api_integration_test_gate` | claude-env | 2026-08 | text+state | API integration test gate. Fires on git commit. When staged files include importer source files (anything unde |
| `azure_sp_identity_guard` | claude-env | 2026-08 | text+state | Azure Service Principal identity guard. Blocks Azure CLI operations when the logged-in service principal doesn |
| `bicep_infra_task_guard` | claude-env | 2026-08 | text+state | Bicep infrastructure task guard. Blocks plan phase file commits that reference Bicep/KeyVault/RBAC infrastruct |
| `bicep_kv_name_guard` | claude-env | 2026-08 | text+state | Bicep Key Vault name guard. Fires on git commit. Scans staged endpoints.json for keyvault source entries (prod |
| `branch_from_main_guard` | claude-env | 2026-08 | text+state | Block branch/worktree creation from main when develop has unmerged commits. Enforces git flow rule: - develop  |
| `cap_task_timeout` | /home/patrick | 2026-08 | other | Agent oversight: cap TaskOutput timeout to prevent indefinite blocking. PreToolUse hook on TaskOutput tool. En |
| `cherry_pick_guard` | claude-env | 2026-08 | text | Block cherry-picks of commits already on the current branch. Exit code 2 = hard block. |
| `cross_repo_fix_audit` | claude-env | 2026-08 | text+state | Cross-repo fix audit. Fires AFTER git commit when the commit message starts with "fix:" or "fix!:" and committ |
| `develop_pr_state_guard` | claude-env | 2026-08 | text+state | Develop PR state guard. Fires on git push. Blocks push to develop when the most recent PR from develop to main |
| `dotnet_process_guard` | claude-env | 2026-08 | text | Verify correct dotnet process is serving. Exit code 2 = hard block. |
| `endpoint_registry_guard` | claude-env | 2026-08 | text+state | Endpoint registry guard. Fires on git commit. Scans staged files for hardcoded connection strings and direct e |
| `endpoint_schema_validator` | claude-env | 2026-08 | text+state | Endpoint schema validator. Fires on git commit. Validates endpoints.json against its schema when the file is b |
| `env_contract_coverage_guard` | claude-env | 2026-08 | text+state | Environment contract coverage guard. Fires on git commit. Extracts every "key" from "source": "env" entries in |
| `eodhd_rebuild_guard` | claude-env, claudeProjects | 2026-08 | text+state | After any git commit that touches eodhd-loader files, inject a mandatory reminder to kill, rebuild, and relaun |
| `git_commit_guard` | /home/patrick, claude-env, claudeProjects | 2026-08 | text | Guard git commit operations. Enforces CLAUDE.md rules: - Must show status, diff, log before commit - Must wait |
| `infra_commit_checklist` | claude-env | 2026-08 | text+state | Infrastructure commit checklist. Fires before git commit when staged files include infrastructure patterns. In |
| `keyvault_secret_name_guard` | claude-env | 2026-08 | text+state | Key Vault secret name guard. Fires on git commit. Validates KV secret names conform to Azure naming rules (^[a |
| `merged_pr_guard` | /home/patrick, claude-env, claudeProjects | 2026-08 | text | Block updates to already-merged/closed PRs. Enforces rule: - NEVER edit or update a PR that has already been m |
| `mock_test_guard` | claude-env, claudeProjects | 2026-08 | text+state | Mock-only test guard. Fires on git commit. Detects new C# test files that use only mocks (Mock<T>, Substitute. |
| `plan_api_url_guard` | claude-env | 2026-08 | text+state | Plan API URL guard. Fires on git commit. When NEWLY ADDED markdown files in docs/implementation-plans/ or docs |
| `plan_commit_guard` | claude-env | 2026-08 | text | Block git push when plan docs are untracked. Exit code 2 = hard block. |
| `plan_config_drift_guard` | claude-env, claudeProjects | 2026-08 | text+state | Plan-config drift guard. Fires on git commit. Scans staged diff for two anti-patterns: 1. EXISTENCE-ONLY VERIF |
| `post_push_pr_check` | /home/patrick, claude-env, claudeProjects | 2026-08 | text | After any git push, check PR state and inject reminder. Problem this solves: After pushing commits to develop, |
| `pr_state_injector` | claude-env | 2026-08 | text+state | Inject current PR state on every git/gh command. Problem this solves: Claude remembers the PR state from when  |
| `pre_push_merged_branch_guard` | claude-env | 2026-08 | text | Block git push when the current branch's PR is already merged/closed. Exit code 2 = hard block. |
| `prices_scan_guard` | claude-env, claudeProjects | 2026-08 | text+state | Prices table full-scan guard. Fires on git commit. Scans staged diff for newly added code that introduces data |
| `workaround_guard` | claude-env, claudeProjects | 2026-08 | text+state | Workaround-instead-of-root-cause-fix guard. Fires on git commit. Scans staged diff for two workaround smells:  |

## Wired and tested — 11

No action.

| hook | wired in | last touched | technique | what it guards |
|---|---|---|---|---|
| `agent_working_tree_guard` | /home/patrick | 2026-08 | other | agent_working_tree_guard.py — PostToolUse hook for the Agent tool. After every subagent dispatch, inspect git  |
| `agent_working_tree_snapshot` | /home/patrick | 2026-08 | state | agent_working_tree_snapshot.py — PreToolUse hook for the Agent tool. Writes `git status --porcelain` for CWD t |
| `agent_worktree_default_guard` | /home/patrick | 2026-06 | other | agent_worktree_default_guard.py — PreToolUse hook for the Agent tool. Forces isolation="worktree" on every Age |
| `ci_cost_guard` | /home/patrick | 2026-07 | text+state | CI cost guard. Background: 2026-07-08 — a Claude instance submitted three needless iOS builds to GitHub Action |
| `defer_forever_guard` | claude-env | 2026-06 | text | Block deferred items that lack Owner + Due date. Background: across multiple retrospectives, items marked as " |
| `design_signoff_guard` | photo-portfolio | 2026-07 | text | Design sign-off gate. Background: photo-portfolio's emphasis feature burned ~30h across three implementation a |
| `gate_git_commit` | /home/patrick | 2026-08 | text | Commit gate: force user approval before a git commit, unless a ticket already answered the question. PreToolUs |
| `main_branch_guard` | /home/patrick, claude-env, claudeProjects | 2026-08 | text | Block dangerous git and destructive operations. Enforces CLAUDE.md rules: - NEVER commit directly to main - NE |
| `park_before_toss_guard` | /home/patrick | 2026-07 | text | Park before toss. Background: 2026-07-08 (photo-portfolio emphasis span-layout, attempt 3). A full day of code |
| `plan_ac_drift_guard` | photo-portfolio | 2026-08 | text+state | AC descope-drift guard. Fires on `git commit` when staged files touch docs/implementation-plans/<slug>/{test-r |
| `plan_staleness_scan` | /home/patrick | 2026-07 | other | Plan-staleness scan. Closes the one gap plan_descope_drift_guard.py (PreToolUse/git-commit) can't: that hook o |


## The finding that supersedes the prune

Found while checking whether the deletion candidates were safe to remove.

```
hooks on disk                       75
invoked with python3 (actually run) 16
invoked ONLY with missing 'python'  44
never execute at all                59
```

`python` is not on this machine — only `python3` is. Every hook wired through
`claude-env/.claude/settings.local.json` is invoked as `python .claude/hooks/x.py`
and dies with `sh: 1: python: not found`. **They fail open**: the hook errors,
Claude Code logs it, and the tool call proceeds.

The 16 that do run are all wired in `~/.claude/settings.json` with `python3`, and
are precisely the ones observed firing during this session — `main_branch_guard`,
`park_before_toss_guard`, `merged_pr_guard`, `gate_git_commit`, `deploy_guard`
and the rest.

This was visible earlier today: the editor crash logged
`Hook PreToolUse:Bash (PreToolUse) error: /bin/sh: 1: python: not found`
repeatedly, and it was read as noise.

**This reframes stage 2.** The question was which hooks to delete. The answer is
that 44 guards believed to be running are not, and the prune matters far less
than that.

**Do not simply fix the interpreter.** One `sed` would activate 44 untested
guards simultaneously. The 16 that do run produced nine false positives in two
days; turning on 44 more, none of them tested, would make the workspace
unusable. That is stage 3's problem, and the bypass corpus is the safety net for
it.

### Three deletions withheld

`branch_churn_guard`, `ef_migration_guard` and `stale_path_guard` are all listed
in `tooling-manifest.json`, the public contract `claude-mac-env` bootstraps from.
Removing them is a coordinated change with an external consumer, not a local
tidy-up — the same reasoning Patrick applied to `manifest_classification_guard`.
Held until that repo is overhauled.

## What this costs today

- **18 of the 104 fixture tests** exercise hooks that fire nowhere.
  They pass, they take time, and they protect nothing that runs.
- Two of the unwired hooks do things we filed tickets to build this week:
  `retro_trigger_guard` (cf. CH-24) and `regression_test_red_verify`. Unwired is
  not the same as unwanted.
- `manifest_classification_guard` is 336 lines, state-based, and fires nowhere —
  the single largest piece of inert code in the repo.

## Recommendation

Not a decision, a starting position:

1. **Wire, do not delete, the two that duplicate planned work.** Building CH-24
   when `retro_trigger_guard` already exists would be the worst outcome available.
2. **Delete the ones that fire nowhere, have no fixtures, and predate August** —
   they were written for a workflow that has since changed.
3. **Leave the 24 in REVIEW alone for now.** They are running. Untested is not
   broken, and stage 3 will establish whether the tests we would write for them
   would find anything.

The point of stage 2 was to avoid testing code that should not exist. That is
achieved by resolving the 13, not by touching the 24.


---

## Addendum, 2026-08-09 evening: what running them changed

This inventory was built by reading hooks — their wiring, their dates, their
docstrings. CH-47 then ran all 13 activated hooks against real payloads and
built 42 fixtures. Reading and running disagreed, and running won every time.
The table above should be read with these corrections.

**The activation itself was unsafe.** All 13 were wired as
`python3 .claude/hooks/x.py` — relative. From any subdirectory the path does not
resolve, the hook errors, and a PreToolUse error aborts the tool call. Two of
them match `PreToolUse/*`, so Bash, Read, Write and Edit were all refused, with
no recovery from inside the session. The pre-flight that cleared the activation
ran from the repo root, the one directory where this is invisible. Now absolute,
and 13/13 verified to resolve from a subdirectory.

**"Wired and running" was not the same as working.** The runner's vocabulary was
PASS/BLOCK — exit 0 versus exit 2 — and every advisory hook always exits 0. A
hook doing its job and a hook doing nothing produced identical observations.
That is the whole reason "13 of 13 ran clean" meant nothing.

**Three corrections to specific rows:**

- `artifact_path_guard` is **inert**, not active. It read a registry that does
  not exist, `load_registry()` swallowed the failure, and every write returned 0
  before a path was compared. Fixed in CH-58 to read the target repo's registry;
  it also **crashed** on the first registry it ever saw (`KeyError` on an
  optional field), which for a PreToolUse hook means blocking the write.
- `ac_staleness_guard` fires on every push here — claude-env has 14 of 14
  criteria unverified — but writes plain text to **stderr** and emits no
  `additionalContext`, unlike its peers. Its message appeared zero times across
  many pushes on 2026-08-09. It has been shouting into the void. Still unfixed:
  changing what appears on every push deserves its own ticket.
- `stale_path_guard` ran `git diff --cached` against **claude-env's index**
  while judging commits in other repos. Fixed in CH-58; still inert (batch 2).

**Two hooks judged prose.** `commit_claim_verify_guard` and
`prod_target_verify_guard` fired on the text of the fixture files being written
to test them — heredoc bodies, not commands. That is AC3's question answered by
accident in ten minutes rather than by waiting a week. Both fixed, and the class
is now held by `tests/test_prose_is_not_a_command.py`, which feeds every
command-scanning hook a document full of dangerous-looking prose and asserts
none of them speaks.

**A grep audit would have been wrong.** Searching hooks for
`strip_heredoc_bodies` said 56 of 62 were offenders. Running the payload said 2.

### What this means for the deletion decision

The recommendation stands but its basis has changed. The case for resolving the
13 unwired hooks is no longer "they are untested"; it is that being wired and
being useful turned out to be unrelated properties, and only running them
distinguishes the two. Any row in the table above that has not been run should
be treated as unverified, including the rows this addendum does not correct.
