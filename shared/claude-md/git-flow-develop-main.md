# Git Flow (develop → main)

<!-- Canonical source: claude-env/shared/claude-md/git-flow-develop-main.md. -->
<!-- Branch names are LITERAL, not parameterised (CE-5.6): every repo using -->
<!-- this fragment is develop -> main, eight of eight, so the variable had one -->
<!-- value and was the only reason these repos still copied their git-flow -->
<!-- rules instead of linking them. A different two-branch layout needs a new -->
<!-- fragment, not a re-added variable. See docs/decisions.md. -->
<!-- Repos that do not follow this flow (e.g. a single-trunk `master` model) should -->
<!-- omit this fragment and document their flow in CLAUDE.local.md. -->

A rule written as `specs/<file>.md#<section>` is held by that section of the spec corpus, in claude-harness's `plugins/psford-tickets/specs/`. Read the section before acting on the rule.

## Critical Git Checkpoints

| Checkpoint | Rule | Enforcement |
|------------|------|-------------|
| **COMMITS** | Show status → diff → log → message → WAIT for explicit approval. A question is NOT approval. | Hook reminds; manual |
| **main BRANCH** | NEVER commit, merge, push --force, or rebase on `main`. | **BLOCKED** |
| **REVERSE MERGE** | NEVER merge `main` INTO `develop` (flow is `develop` → `main` only). | **BLOCKED** |
| **PR MERGE (main)** | Patrick merges via GitHub web only — NEVER `gh pr merge` on a PR targeting `main`. Every flow repo requires 1 approving review on `main` (2026-10-01); the robot cannot approve its own PRs, so it can never land `main` alone. | **BLOCKED** |
| **PR MERGE (develop)** | The robot MAY `gh pr merge` its own feature→develop PRs once green. This is the robot's merge lane; `main` never is. | Allowed |
| **HOTFIX (main)** | Patrick may push `main` directly in an emergency — his owner bypass is the sole direct-to-main path (`enforce_admins` is off). | Patrick-only |
| **MERGED PRs** | NEVER edit/push to merged/closed PRs. Always create a NEW PR. | **BLOCKED** |
| **NO RESET --HARD** | NEVER run `git reset --hard` (it destroyed uncommitted work once). Use `git merge`/`git rebase` to sync; `git stash` first if the tree is dirty. | **BLOCKED** |

## Branching Strategy

```
develop (work here) → PR → main (production)
                                  ↑
                           NEVER reverse this
```

- **When to branch, and the check before branching:** `specs/git.md#branching`
- **NEVER** commit directly to `main`, merge to it via CLI, deploy without an explicit "deploy", or click "Update branch" on the GitHub PR page.

### Forbidden Operations (on develop)
| Operation | Why |
|-----------|-----|
| `git merge main` | `develop` flows TO `main` only |
| `git pull origin main` | Pulls and merges `main` into `develop` |
| `git rebase main` | Rewrites `develop` history based on `main` |

If the branches diverge, merge `develop` into `main` via PR — never the reverse.

## PR Rules

- **Approvals across the gate:** the robot approves Patrick's PRs (that is how
  the `main` review gate is satisfied); Patrick approves the robot's `main`
  PRs and merges them on the web. The robot never approves its own PRs
  (GitHub blocks that) and never merges `main`.
- **Checking a PR:** `specs/git.md#verify-git-and-pr-state`
- **After a push, and after a merge:** `specs/git.md#release-prs`

## Pre-Commit Protocol

Before every commit, show Patrick:
1. `git status` — staged, unstaged, untracked
2. `git diff` — actual changes
3. `git log -3` — recent commits for style
4. Planned commit message
5. What will NOT happen (no `main`, no deploy, no PR)

Then **WAIT for explicit approval**. A question or comment resets the checkpoint — answer it, then wait again. Also verify: `claudeLog.md` updated, all files staged, feature tested.
