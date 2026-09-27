# The fixture vacuity sweep — 2026-09-27

**CE-2.96.** Replaces CE-2.24, whose method contradicted its own controls
(see that ticket's description). The corrected question: **which fixtures
that expect their hook to act (BLOCK or FIRES) still pass when the hook
does nothing?** Those are vacuous. A PASS or SILENT fixture passing under a
no-op is expected and excluded by construction — it is not evaluated here.

## Method

Every fixture directory under `.claude/hooks/tests/` has a matching
`<hook>.py` in `.claude/hooks/` and, in every case, a per-hook `_invoke.sh`
driver. In a scratch copy of the repo at `/tmp/ce296-sweep` (`cp -a`, never
the real worktree's `.claude/hooks/`), each hook was replaced in turn with a
no-op script:

```python
import sys
sys.stdin.read()
sys.exit(0)
```

`bash /tmp/ce296-sweep/.claude/hooks/tests/run-hook-tests.sh <hook>` was run
against the scratch copy for that one hook (absolute path, cwd passed
explicitly via `subprocess.run(cwd=...)` — the scratch copy was never `cd`ed
into), then the original hook file was restored before moving to the next
hook, so no two hooks were ever neutered at once. The driver script and the
one that ran the sweep: `/home/patrick/.local/share/harness/ce224/sweep.py`.
Full raw runner output: `/home/patrick/.local/share/harness/ce224/sweep_raw.log`;
the fixture-level lines only (headings, ✓/✗ per fixture, ANSI stripped):
`/home/patrick/.local/share/harness/ce224/sweep_clean.log`.

A fixture "survives" here if the runner still shows `✓` for it — expectation
met — with its hook doing nothing. Every fixture directory that exists is
listed below, in the order `run-hook-tests.sh` visits them, each command and
log the same for every row: `bash .claude/hooks/tests/run-hook-tests.sh
<hook>` against the neutered scratch copy, output captured in
`sweep_raw.log` under the `=== <hook> ===` heading.

## Result

**Zero fixtures survived, anywhere.** 177 BLOCK/FIRES fixtures were swept
across the 37 fixture directories (36 with at least one BLOCK/FIRES fixture;
`pr_state_injector` has none — its fixtures are all PASS/SILENT). None of the
177 still passed with its hook replaced by a no-op. Every directory below is
listed with a 0/N survivor count and no entries to rank.

This includes both of the fixtures the previous, contradictory sweep (CE-2.24)
used as controls:

- **`retro_area_overlap_guard` fixture 01** (`01-new-file-in-a-tagged-area.FIRES.md`)
  does **not** survive: `✗ ... (FIRES via _invoke.sh, driver rc=1) — expected
  the hook to speak, it said nothing`. It is not listed as surviving, matching
  AC3.
- **`shadow_command_guard` fixtures 22 and 23** are PASS fixtures
  (`22-a-relative-path-names-the-payloads-repo.PASS.md`,
  `23-a-relative-fixture-into-an-existing-suite.PASS.md`), so they are
  excluded from consideration by construction (not BLOCK or FIRES) and are
  not listed as surviving, matching AC3.

## Every fixture directory, ranked by survivors (all 0)

| Directory | BLOCK/FIRES fixtures | Survived |
|---|---|---|
| `ci_cost_guard` | 38 | 0 |
| `main_branch_guard` | 26 | 0 |
| `deploy_guard` | 25 | 0 |
| `shadow_command_guard` | 17 | 0 |
| `agent_worktree_default_guard` | 9 | 0 |
| `agent_working_tree_guard` | 4 | 0 |
| `pr_after_accept_guard` | 4 | 0 |
| `shared_rules_link_guard` | 5 | 0 |
| `visual_ac_manual_guard` | 6 | 0 |
| `commit_message_substitution_guard` | 3 | 0 |
| `design_signoff_guard` | 3 | 0 |
| `mutation_harness_guard` | 3 | 0 |
| `park_before_toss_guard` | 3 | 0 |
| `regression_test_red_verify` | 3 | 0 |
| `cwd_drift_guard` | 2 | 0 |
| `defer_forever_guard` | 2 | 0 |
| `merged_pr_guard` | 2 | 0 |
| `stderr_suppression_guard` | 2 | 0 |
| `absolute_path_link_guard` | 1 | 0 |
| `ac_staleness_guard` | 1 | 0 |
| `artifact_path_guard` | 1 | 0 |
| `assert_verify_guard` | 1 | 0 |
| `branch_from_main_guard` | 1 | 0 |
| `commit_claim_verify_guard` | 1 | 0 |
| `cross_repo_fix_audit` | 1 | 0 |
| `eodhd_rebuild_guard` | 1 | 0 |
| `feasibility_spike_guard` | 1 | 0 |
| `fix_commit_smell_guard` | 1 | 0 |
| `infra_commit_checklist` | 1 | 0 |
| `plan_ac_drift_guard` | 1 | 0 |
| `plan_descope_drift_guard` | 1 | 0 |
| `plan_staleness_scan` | 1 | 0 |
| `pr_migration_checklist` | 1 | 0 |
| `prod_target_verify_guard` | 1 | 0 |
| `retro_area_overlap_guard` | 1 | 0 |
| `shellcheck_write_guard` | 1 | 0 |
| `simplest_path_guard` | 1 | 0 |
| `spec_staleness_guard` | 1 | 0 |
| `pr_state_injector` | 0 | 0 (no BLOCK/FIRES fixtures in this directory; all PASS/SILENT — run recorded below for completeness) |

Command and log for every row above: `bash
/tmp/ce296-sweep/.claude/hooks/tests/run-hook-tests.sh <hook>` with `<hook>.py`
replaced by the no-op, cwd `/tmp/ce296-sweep`; full output in
`/home/patrick/.local/share/harness/ce224/sweep_raw.log` under `=== <hook>
=== (N BLOCK/FIRES fixtures, 0 survived)`; per-fixture ✓/✗ lines in
`/home/patrick/.local/share/harness/ce224/sweep_clean.log`.

## Why this differs from CE-2.24's uniform-file-swap intuition

Every one of these 37 directories has its own `_invoke.sh` driver (not the
runner's default synthetic-`git commit` rc-check), so a no-op's empty output
and rc 0 do not just fail to match an expected BLOCK rc — the drivers
independently assert on repo state, hook stdout, or fixture-specific markers,
and every one of them noticed the hook went silent or the state it expected
never appeared. That is the corrected sweep's finding: on this hook suite,
as it stands on 2026-09-27, there is no BLOCK or FIRES fixture whose pass
does not depend on its hook actually running.
