# Security Issue: GitHub CLI Token Has Excessive Scope

**Date:** 2026-03-31
**Severity:** Medium
**Status:** Mitigated

## Problem

The `gh` CLI token authenticated in WSL2 has `repo` scope, which includes Actions write access — enough to trigger `workflow_dispatch` deployments programmatically.

## Threat Model

The concern is Claude autonomously triggering production deploys, not Patrick using `gh` from his own terminal.

## Mitigations (Sufficient)

- `deploy_guard.py` hook **hard-blocks** `gh workflow run` from within Claude Code sessions
- Deploy workflow requires manual `confirm_deploy=deploy` input
- Patrick retains full `gh` CLI access from terminal for manual deploys

## Future Hardening (Optional)

If the WSL2 environment is ever shared or exposed beyond Patrick's terminal, consider replacing the classic PAT with a fine-grained token that grants Actions: Read only.
