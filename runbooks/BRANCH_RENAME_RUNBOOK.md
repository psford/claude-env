# Branch Rename Runbook

Step-by-step procedure for renaming a Git branch (e.g., `master` → `main`).

**Last used:** 2026-01-19 (master → main rename)

---

## Prerequisites

- Git CLI installed
- GitHub CLI (`gh`) installed and authenticated
- Push access to the repository
- Admin access to modify branch protection rules

---

## Procedure

### Step 1: Rename Local Branch

```bash
git checkout <old-branch>
git branch -m <old-branch> <new-branch>
```

Example:
```bash
git checkout master
git branch -m master main
```

### Step 2: Push New Branch to Remote

```bash
git push -u origin <new-branch>
```

Example:
```bash
git push -u origin main
```

### Step 3: Update GitHub Default Branch

```bash
gh repo edit --default-branch <new-branch>
```

Example:
```bash
gh repo edit --default-branch main
```

### Step 4: Transfer Branch Protection Rules

First, get existing protection rules from old branch:

```bash
gh api repos/<owner>/<repo>/branches/<old-branch>/protection
```

Then apply to new branch (adjust JSON as needed):

```bash
gh api repos/<owner>/<repo>/branches/<new-branch>/protection --method PUT --input - << 'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["build"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

**Note:** Adjust the JSON to match your existing protection settings. The GET response shows the current config.

### Step 5: Remove Protection from Old Branch

```bash
gh api repos/<owner>/<repo>/branches/<old-branch>/protection --method DELETE
```

### Step 6: Delete Old Branch from Remote

```bash
git push origin --delete <old-branch>
```

Example:
```bash
git push origin --delete master
```

**Note:** If you get "protected branch hook declined", ensure Step 5 completed successfully.

### Step 7: Update Documentation References

Search for and update all references to the old branch name:

**Files commonly affected:**
- `CLAUDE.md` or similar guidelines
- `README.md`
- `sessionState.md` or state files
- `.github/workflows/*.yml` (most already use `[master, main]` patterns)
- CI/CD configuration files
- Documentation referencing the branch

**Search command:**
```bash
grep -r "master" --include="*.md" --include="*.yml" --include="*.yaml" .
```

### Step 8: Commit Documentation Changes

```bash
git add -A
git commit -m "Rename <old-branch> branch to <new-branch>

- Renamed production branch from '<old-branch>' to '<new-branch>'
- Updated all documentation references
- Branch protection rules transferred to new branch"

git push origin <current-branch>
```

---

## Verification Checklist

After completing the rename:

- [ ] `git branch -a` shows new branch locally and on remote
- [ ] Old branch no longer exists on remote
- [ ] GitHub repo settings show new branch as default
- [ ] Branch protection rules are active on new branch
- [ ] CI/CD workflows trigger correctly on new branch
- [ ] All documentation references updated

---

## Rollback

If something goes wrong, you can reverse the process:

1. Rename local branch back: `git branch -m <new-branch> <old-branch>`
2. Push old branch: `git push -u origin <old-branch>`
3. Reset default: `gh repo edit --default-branch <old-branch>`
4. Transfer protection rules back
5. Delete new branch: `git push origin --delete <new-branch>`

---

## Common Issues

### "Protected branch hook declined" when deleting

The old branch still has protection rules. Run Step 5 first.

### CI workflows not triggering

Most workflows use `[master, main]` in their `on:` triggers. If yours doesn't, update the workflow file to include the new branch name.

### Pull requests targeting old branch

Any open PRs targeting the old branch will need to be retargeted to the new branch manually, or closed and recreated.

---

## Reference

- GitHub docs: [Renaming a branch](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/renaming-a-branch)
- Our execution: 2026-01-19, `master` → `main` in claudeProjects repo
