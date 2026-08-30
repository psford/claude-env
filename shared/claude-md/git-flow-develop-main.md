# Git Flow (develop → main)

<!-- Canonical source: claude-env/shared/claude-md/git-flow-develop-main.md. -->
<!-- Branch names are LITERAL, not parameterised (CE-5.6): every repo using -->
<!-- this fragment is develop -> main, eight of eight, so the variable had one -->
<!-- value and was the only reason these repos still copied their git-flow -->
<!-- rules instead of linking them. A different two-branch layout needs a new -->
<!-- fragment, not a re-added variable. See docs/decisions.md. -->
<!-- Repos that do not follow this flow (e.g. a single-trunk `master` model) should -->
<!-- omit this fragment and document their flow in CLAUDE.local.md. -->

## Critical Git Checkpoints

| Checkpoint | Rule | Enforcement |
|------------|------|-------------|
| **COMMITS** | Show status → diff → log → message → WAIT for explicit approval. A question is NOT approval. | Hook reminds; manual |
| **main BRANCH** | NEVER commit, merge, push --force, or rebase on `main`. | **BLOCKED** |
| **REVERSE MERGE** | NEVER merge `main` INTO `develop` (flow is `develop` → `main` only). | **BLOCKED** |
| **PR MERGE** | Patrick merges via GitHub web only — NEVER use `gh pr merge`. | **BLOCKED** |
| **MERGED PRs** | NEVER edit/push to merged/closed PRs. Always create a NEW PR. | **BLOCKED** |
| **NO RESET --HARD** | NEVER run `git reset --hard` (it destroyed uncommitted work once). Use `git merge`/`git rebase` to sync; `git stash` first if the tree is dirty. | **BLOCKED** |

## Branching Strategy

```
develop (work here) → PR → main (production)
                                  ↑
                           NEVER reverse this
```

- **Feature branches** for: new services, architecture changes, multi-file refactors, big UI changes, multi-session work, 5+ files.
- **Direct on `develop`** for: small fixes, tweaks, internal docs.
- **NEVER** commit directly to `main`, merge to it via CLI, deploy without an explicit "deploy", or click "Update branch" on the GitHub PR page.
- Before branching: `git fetch origin` and check `git log origin/main..develop` — never assume branches are in sync, and never offer to reuse the current branch without confirming it isn't `main`.

### Forbidden Operations (on develop)
| Operation | Why |
|-----------|-----|
| `git merge main` | `develop` flows TO `main` only |
| `git pull origin main` | Pulls and merges `main` into `develop` |
| `git rebase main` | Rewrites `develop` history based on `main` |

If the branches diverge, merge `develop` into `main` via PR — never the reverse.

## PR Rules

**Verification — when asked to check a PR:**
1. `git fetch origin` (ALWAYS fetch first).
2. `git log origin/main..develop --oneline` (ALWAYS `origin/main`, not local).
3. `gh pr view <N> --json commits` to see what's in the PR.
4. Report the delta — never just update PR title/body. Never assert PR state from memory; confirm with `gh pr view`.

**Merged PRs** — once merged/closed, a PR is DEAD. After any `git push`:
1. Check `gh pr list --head develop --base main --state open`.
2. No open PR → create a NEW one. Never reference old PR numbers without checking state. If Patrick is deploying, the previous PR is already merged — create a new PR for any follow-up fix.

## Pre-Commit Protocol

Before every commit, show Patrick:
1. `git status` — staged, unstaged, untracked
2. `git diff` — actual changes
3. `git log -3` — recent commits for style
4. Planned commit message
5. What will NOT happen (no `main`, no deploy, no PR)

Then **WAIT for explicit approval**. A question or comment resets the checkpoint — answer it, then wait again. Also verify: `claudeLog.md` updated, all files staged, feature tested.
