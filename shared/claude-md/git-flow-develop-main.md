# Git Flow ({{WORKING_BRANCH}} → {{PRODUCTION_BRANCH}})

<!-- Canonical source: claude-env/shared/claude-md/git-flow-develop-main.md. -->
<!-- Branch names are parameterized: {{WORKING_BRANCH}} / {{PRODUCTION_BRANCH}}. -->
<!-- Repos that do not follow this flow (e.g. a single-trunk `master` model) should -->
<!-- omit this fragment and document their flow in CLAUDE.local.md. -->

## Critical Git Checkpoints

| Checkpoint | Rule | Enforcement |
|------------|------|-------------|
| **COMMITS** | Show status → diff → log → message → WAIT for explicit approval. A question is NOT approval. | Hook reminds; manual |
| **{{PRODUCTION_BRANCH}} BRANCH** | NEVER commit, merge, push --force, or rebase on `{{PRODUCTION_BRANCH}}`. | **BLOCKED** |
| **REVERSE MERGE** | NEVER merge `{{PRODUCTION_BRANCH}}` INTO `{{WORKING_BRANCH}}` (flow is `{{WORKING_BRANCH}}` → `{{PRODUCTION_BRANCH}}` only). | **BLOCKED** |
| **PR MERGE** | Patrick merges via GitHub web only — NEVER use `gh pr merge`. | **BLOCKED** |
| **MERGED PRs** | NEVER edit/push to merged/closed PRs. Always create a NEW PR. | **BLOCKED** |
| **NO RESET --HARD** | NEVER run `git reset --hard` (it destroyed uncommitted work once). Use `git merge`/`git rebase` to sync; `git stash` first if the tree is dirty. | **BLOCKED** |

## Branching Strategy

```
{{WORKING_BRANCH}} (work here) → PR → {{PRODUCTION_BRANCH}} (production)
                                  ↑
                           NEVER reverse this
```

- **Feature branches** for: new services, architecture changes, multi-file refactors, big UI changes, multi-session work, 5+ files.
- **Direct on `{{WORKING_BRANCH}}`** for: small fixes, tweaks, internal docs.
- **NEVER** commit directly to `{{PRODUCTION_BRANCH}}`, merge to it via CLI, deploy without an explicit "deploy", or click "Update branch" on the GitHub PR page.
- Before branching: `git fetch origin` and check `git log origin/{{PRODUCTION_BRANCH}}..{{WORKING_BRANCH}}` — never assume branches are in sync, and never offer to reuse the current branch without confirming it isn't `{{PRODUCTION_BRANCH}}`.

### Forbidden Operations (on {{WORKING_BRANCH}})
| Operation | Why |
|-----------|-----|
| `git merge {{PRODUCTION_BRANCH}}` | `{{WORKING_BRANCH}}` flows TO `{{PRODUCTION_BRANCH}}` only |
| `git pull origin {{PRODUCTION_BRANCH}}` | Pulls and merges `{{PRODUCTION_BRANCH}}` into `{{WORKING_BRANCH}}` |
| `git rebase {{PRODUCTION_BRANCH}}` | Rewrites `{{WORKING_BRANCH}}` history based on `{{PRODUCTION_BRANCH}}` |

If the branches diverge, merge `{{WORKING_BRANCH}}` into `{{PRODUCTION_BRANCH}}` via PR — never the reverse.

## PR Rules

**Verification — when asked to check a PR:**
1. `git fetch origin` (ALWAYS fetch first).
2. `git log origin/{{PRODUCTION_BRANCH}}..{{WORKING_BRANCH}} --oneline` (ALWAYS `origin/{{PRODUCTION_BRANCH}}`, not local).
3. `gh pr view <N> --json commits` to see what's in the PR.
4. Report the delta — never just update PR title/body. Never assert PR state from memory; confirm with `gh pr view`.

**Merged PRs** — once merged/closed, a PR is DEAD. After any `git push`:
1. Check `gh pr list --head {{WORKING_BRANCH}} --base {{PRODUCTION_BRANCH}} --state open`.
2. No open PR → create a NEW one. Never reference old PR numbers without checking state. If Patrick is deploying, the previous PR is already merged — create a new PR for any follow-up fix.

## Pre-Commit Protocol

Before every commit, show Patrick:
1. `git status` — staged, unstaged, untracked
2. `git diff` — actual changes
3. `git log -3` — recent commits for style
4. Planned commit message
5. What will NOT happen (no `{{PRODUCTION_BRANCH}}`, no deploy, no PR)

Then **WAIT for explicit approval**. A question or comment resets the checkpoint — answer it, then wait again. Also verify: `claudeLog.md` updated, all files staged, feature tested.
