# Hook wiring inventory

2026-09-27. Read-only enumeration for CE-2.21: which of this worktree's
.claude/hooks/*.py files are wired in a settings file or plugin hooks.json,
and where. Method, raw output, and the enumeration script are kept at
/home/patrick/.local/share/harness/ce221/ (enumerate.py, settings_files.txt,
hook_basenames.txt, wiring.json, enumerate_output.txt) and are not committed.

91 hook files total; 56 wired somewhere; 35 wired nowhere. Two rows added
later the same day, both SessionStart: agent_worktree_sweep (CE-2.98), and
plugin_cache_integrity (CE-2.101), which is 93, 58 and 35.

## Table

| Hook | Wired |
|---|---|
| _repo_context | wired nowhere |
| absolute_path_link_guard | global:~/.claude/settings.json:Stop |
| ac_staleness_guard | claude-env/.claude/settings.local.json:PostToolUse, <windows-root>/.claude/settings.local.json:PostToolUse |
| agent_model_guard | global:~/.claude/settings.json:PreToolUse (Agent\|Workflow) |
| agent_refusal_tally | global:~/.claude/settings.json:PostToolUse |
| agent_working_tree_guard | global:~/.claude/settings.json:PostToolUse |
| agent_working_tree_snapshot | global:~/.claude/settings.json:PreToolUse |
| agent_worktree_default_guard | global:~/.claude/settings.json:PreToolUse |
| agent_worktree_sweep | global:~/.claude/settings.json:SessionStart |
| api_integration_test_gate | wired nowhere |
| artifact_path_guard | claude-env/.claude/settings.local.json:PreToolUse, <windows-root>/.claude/settings.local.json:PreToolUse |
| assert_verify_guard | claude-env/.claude/settings.local.json:PreToolUse, <windows-root>/.claude/settings.local.json:PreToolUse |
| azure_sp_identity_guard | wired nowhere |
| bicep_infra_task_guard | wired nowhere |
| bicep_kv_name_guard | wired nowhere |
| branch_churn_guard | wired nowhere |
| branch_from_main_guard | claude-env/.claude/settings.local.json:PreToolUse |
| browser_compat_guard | wired nowhere |
| cap_task_timeout | global:~/.claude/settings.json:PreToolUse |
| cherry_pick_guard | wired nowhere |
| ci_cost_guard | global:~/.claude/settings.json:PreToolUse |
| clyde_dispatch_review_guard | global:~/.claude/settings.json:PreToolUse |
| commit_claim_verify_guard | claude-env/.claude/settings.local.json:PreToolUse |
| commit_message_substitution_guard | global:~/.claude/settings.json:PreToolUse |
| constant_change_test_guard | wired nowhere |
| cross_repo_fix_audit | claude-env/.claude/settings.local.json:PostToolUse |
| cwd_drift_guard | global:~/.claude/settings.json:PreToolUse |
| defer_forever_guard | claude-env/.claude/settings.local.json:PreToolUse |
| deploy_guard | <windows-root>/.claude/settings.local.json:PreToolUse, global:~/.claude/settings.json:PreToolUse |
| deprecation_guard | <windows-root>/.claude/settings.local.json:PostToolUse, global:~/.claude/settings.json:PostToolUse |
| design_signoff_guard | photo-portfolio/.claude/settings.json:PreToolUse |
| develop_pr_state_guard | wired nowhere |
| dotnet_process_guard | wired nowhere |
| ef_migration_guard | wired nowhere |
| endpoint_registry_guard | wired nowhere |
| endpoint_schema_validator | wired nowhere |
| engines_node_guard | wired nowhere |
| env_contract_coverage_guard | wired nowhere |
| eodhd_rebuild_guard | claude-env/.claude/settings.local.json:PostToolUse, <windows-root>/.claude/settings.local.json:PostToolUse |
| feasibility_spike_guard | claude-env/.claude/settings.local.json:PreToolUse |
| fix_commit_smell_guard | claude-env/.claude/settings.local.json:PostToolUse, <windows-root>/.claude/settings.local.json:PostToolUse |
| gate_git_commit | global:~/.claude/settings.json:PreToolUse |
| git_commit_guard | <windows-root>/.claude/settings.local.json:PreToolUse, global:~/.claude/settings.json:PreToolUse |
| hatch_authoring_guard | global:~/.claude/settings.json:PreToolUse |
| hatch_shape_scan | wired nowhere |
| infra_commit_checklist | claude-env/.claude/settings.local.json:PreToolUse |
| js_coordinate_truthiness_guard | wired nowhere |
| js_dead_assignment_guard | wired nowhere |
| js_module_coverage_guard | wired nowhere |
| js_test_theater_guard | wired nowhere |
| keyvault_secret_name_guard | wired nowhere |
| library_intro_guard | wired nowhere |
| main_branch_guard | <windows-root>/.claude/settings.local.json:PreToolUse, global:~/.claude/settings.json:PreToolUse |
| manifest_classification_guard | wired nowhere |
| manifest_completeness_guard | wired nowhere |
| merged_pr_guard | <windows-root>/.claude/settings.local.json:PreToolUse, global:~/.claude/settings.json:PreToolUse |
| mock_test_guard | <windows-root>/.claude/settings.local.json:PreToolUse |
| mutation_harness_guard | global:~/.claude/settings.json:PreToolUse |
| orphan_process_guard | global:~/.claude/settings.json:PreToolUse |
| park_before_toss_guard | global:~/.claude/settings.json:PreToolUse |
| plan_ac_drift_guard | photo-portfolio/.claude/settings.json:PreToolUse |
| plan_api_url_guard | wired nowhere |
| plan_branch_guard | wired nowhere |
| plan_commit_guard | wired nowhere |
| plan_config_drift_guard | <windows-root>/.claude/settings.local.json:PreToolUse |
| plan_descope_drift_guard | claude-env/.claude/settings.local.json:PreToolUse |
| plan_phase_count_guard | wired nowhere |
| plan_staleness_scan | global:~/.claude/settings.json:SessionStart |
| playwright_gate | wired nowhere |
| plugin_cache_integrity | global:~/.claude/settings.json:SessionStart |
| session_integrity | wired nowhere (CE-2.103 built it; the SessionStart writer, then the PreToolUse guard, go into ~/.claude/settings.json through Patrick's approval, in that order) |
| post_push_pr_check | <windows-root>/.claude/settings.local.json:PostToolUse, global:~/.claude/settings.json:PostToolUse |
| pr_after_accept_guard | global:~/.claude/settings.json:PreToolUse |
| pr_migration_checklist | claude-env/.claude/settings.local.json:PreToolUse |
| pr_state_injector | claude-env/.claude/settings.local.json:PostToolUse |
| pre_push_merged_branch_guard | wired nowhere |
| prices_scan_guard | <windows-root>/.claude/settings.local.json:PreToolUse |
| prod_target_verify_guard | claude-env/.claude/settings.local.json:PreToolUse |
| refusal_ends_the_run | global:~/.claude/settings.json:PreToolUse |
| regression_test_red_verify | wired nowhere |
| reply_rule_guard | global:~/.claude/settings.json:Stop |
| retro_area_overlap_guard | claude-env/.claude/settings.local.json:PreToolUse |
| retro_trigger_guard | wired nowhere |
| session_checkpoint | wired nowhere |
| session_start | <windows-root>/.claude/settings.local.json:SessionStart, global:~/.claude/settings.json:SessionStart |
| shadow_command_guard | claude-env/.claude/settings.local.json:PreToolUse |
| shared_rules_link_guard | global:~/.claude/settings.json:PreToolUse |
| shellcheck_write_guard | claude-env/.claude/settings.local.json:PreToolUse, <windows-root>/.claude/settings.local.json:PreToolUse |
| simplest_path_guard | claude-env/.claude/settings.local.json:PreToolUse |
| spec_staleness_guard | claude-env/.claude/settings.local.json:PostToolUse, <windows-root>/.claude/settings.local.json:PostToolUse |
| stale_path_guard | wired nowhere |
| stderr_suppression_guard | claude-env/.claude/settings.local.json:PreToolUse, <windows-root>/.claude/settings.local.json:PreToolUse |
| verification_claim_guard | global:~/.claude/settings.json:Stop |
| visual_ac_manual_guard | claude-env/.claude/settings.local.json:PreToolUse |
| workaround_guard | <windows-root>/.claude/settings.local.json:PreToolUse |

Worktree checkouts (`claude-env--<ID>`) share claude-env's own settings and are left out; the Windows projects root is written `<windows-root>`.

## Wired nowhere

- _repo_context
- api_integration_test_gate
- azure_sp_identity_guard
- bicep_infra_task_guard
- bicep_kv_name_guard
- branch_churn_guard
- browser_compat_guard
- cherry_pick_guard
- constant_change_test_guard
- develop_pr_state_guard
- dotnet_process_guard
- ef_migration_guard
- endpoint_registry_guard
- endpoint_schema_validator
- engines_node_guard
- env_contract_coverage_guard
- hatch_shape_scan
- js_coordinate_truthiness_guard
- js_dead_assignment_guard
- js_module_coverage_guard
- js_test_theater_guard
- keyvault_secret_name_guard
- library_intro_guard
- manifest_classification_guard
- manifest_completeness_guard
- plan_api_url_guard
- plan_branch_guard
- plan_commit_guard
- plan_phase_count_guard
- playwright_gate
- pre_push_merged_branch_guard
- regression_test_red_verify
- retro_trigger_guard
- session_checkpoint
- stale_path_guard

## Incident hooks

- js_test_theater_guard: wired nowhere
- ef_migration_guard: wired nowhere
- api_integration_test_gate: wired nowhere
- cherry_pick_guard: wired nowhere
- stale_path_guard: wired nowhere
- workaround_guard: wired at <windows-root>/.claude/settings.local.json:PreToolUse
