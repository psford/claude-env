# Git Flow (trunk: {{TRUNK_BRANCH}})

<!-- Canonical source: claude-env/shared/claude-md/git-flow-trunk.md. -->
<!-- Trunk-based model: a single integration branch ({{TRUNK_BRANCH}}) that also -->
<!-- deploys. Short-lived feature branches → PR → {{TRUNK_BRANCH}}. Use this fragment -->
<!-- (instead of git-flow-develop-main) for repos with no separate develop branch. -->
<!-- {{TRUNK_BRANCH}} is parameterized (main, master, ...). -->

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
- **Feature branches** (`feature/*`, `fix/*`, `docs/*`) for anything non-trivial: branch → commit → push → PR → CI → merge.
- Keep feature branches short-lived; rebase/merge from `{{TRUNK_BRANCH}}` to stay current (this is the normal direction — there is no separate develop to protect).
- Before branching: `git fetch origin` and check `git log origin/{{TRUNK_BRANCH}}..HEAD`. Never assume sync; never offer to reuse the current branch without confirming it isn't `{{TRUNK_BRANCH}}`.

## PR Rules

**Verification — when asked to check a PR:**
1. `git fetch origin` (ALWAYS fetch first).
2. `git log origin/{{TRUNK_BRANCH}}..<branch> --oneline` to see the delta.
3. `gh pr view <N> --json commits`. Report the delta — never just update PR title/body. Never assert PR state from memory; confirm with `gh pr view`.

**Merged PRs** — once merged/closed, a PR is DEAD. After any `git push`, check for an open PR (`gh pr list --head <branch> --base {{TRUNK_BRANCH}} --state open`); if none, create a NEW one. If Patrick is deploying, the previous PR is already merged — any follow-up fix is a NEW PR.

## Pre-Commit Protocol

Before every commit, show Patrick: `git status` · `git diff` · `git log -3` · the planned message · what will NOT happen (no direct `{{TRUNK_BRANCH}}` commit unless trivial, no deploy, no PR merge). Then **WAIT for explicit approval** — a question resets the checkpoint. Also verify `claudeLog.md` updated, all files staged, feature tested.
