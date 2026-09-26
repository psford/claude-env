# Git Flow (trunk: {{TRUNK_BRANCH}})

<!-- Canonical source: claude-env/shared/claude-md/git-flow-trunk.md. -->
<!-- Trunk-based model: a single integration branch ({{TRUNK_BRANCH}}) that also -->
<!-- deploys. Short-lived feature branches → PR → {{TRUNK_BRANCH}}. Use this fragment -->
<!-- (instead of git-flow-develop-main) for repos with no separate develop branch. -->
<!-- {{TRUNK_BRANCH}} is parameterized (main, master, ...). -->

A rule written as `specs/<file>.md#<section>` is held by that section of the spec corpus, in claude-harness's `plugins/psford-tickets/specs/`. Read the section before acting on the rule.

## Critical Git Checkpoints

| Checkpoint | Rule | Enforcement |
|------------|------|-------------|
| **COMMITS** | Show status → diff → log → message → WAIT for explicit approval. A question is NOT approval. | Hook reminds; manual |
| **NOTHING REACHES {{TRUNK_BRANCH}} EXCEPT VIA PR** | Never commit or push to `{{TRUNK_BRANCH}}` — branch, PR, let CI run. No carve-out for doc or typo fixes. This covers *any* refspec landing on trunk, including `git push origin <branch>:{{TRUNK_BRANCH}}`, which is a CLI merge however it is spelled. Never push --force or rebase `{{TRUNK_BRANCH}}`. | **BLOCKED** server-side (branch protection, `enforce_admins=true`) and locally (`main_branch_guard`) |
| **PR MERGE** | Patrick merges via GitHub web only — NEVER use `gh pr merge`. | **BLOCKED** |
| **MERGED PRs** | NEVER edit/push to merged/closed PRs. Always create a NEW PR. | **BLOCKED** |
| **NO RESET --HARD** | NEVER run `git reset --hard`. Use `git merge`/`git rebase` to sync; `git stash` first if the tree is dirty. | **BLOCKED** |

## Branching Strategy

```
feature/* → PR → {{TRUNK_BRANCH}} (integration + deploy)
```

- `{{TRUNK_BRANCH}}` is the single integration branch and the deploy source.
- **Feature branches, keeping them current, and the check before branching:** `specs/git.md#branching`

## PR Rules

- **Checking a PR, and opening a new one after a push:** `specs/git.md#verify-git-and-pr-state`

## Pre-Commit Protocol

Before every commit, show Patrick: `git status` · `git diff` · `git log -3` · the planned message · what will NOT happen (no direct `{{TRUNK_BRANCH}}` commit unless trivial, no deploy, no PR merge). Then **WAIT for explicit approval** — a question resets the checkpoint. Also verify `claudeLog.md` updated, all files staged, feature tested.
