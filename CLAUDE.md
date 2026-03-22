# CLAUDE.md

Instructions and shared knowledge for Claude Code sessions with **claude-env** — the development environment repo containing reusable tooling, hooks, and helpers.

---

## About Claude-Env

**claude-env** is the isolated development environment repository. It contains:
- **Hooks** (`.claude/hooks/`) — Enforced code quality, pre-commit validation
- **Helpers** (`helpers/`) — Python/PowerShell utilities for security, testing, deployment, Slack integration
- **Infrastructure** (`infrastructure/`) — WSL2 setup contracts, Azure deployment config
- **Design docs** (`docs/`) — Planning, retrospectives, design decisions (historical reference)

This repo is **independent of app implementations**. Companion app repos reference claude-env via bootstrap scripts (created in Phase 6).

**Companion app repos:**
- `psford/stock-analyzer` — Stock analysis web application (.NET)
- `psford/road-trip` — Road trip photo map (future)

---

## CRITICAL CHECKPOINTS (READ FIRST)

Enforced by Claude Code hooks. Violations are blocked automatically.

| Checkpoint | Rule | Enforcement |
|------------|------|-------------|
| **COMMITS** | Show status → diff → log → message → WAIT for explicit approval. A question is NOT approval. | Hook reminds; manual |
| **MAIN BRANCH** | NEVER commit, merge, push --force, or rebase on main | **BLOCKED** |
| **REVERSE MERGE** | NEVER merge main INTO develop (flow is develop → main only) | **BLOCKED** |
| **PR MERGE** | Patrick merges via GitHub web only — NEVER use `gh pr merge` | **BLOCKED** |
| **MERGED PRs** | NEVER edit/push to merged/closed PRs. Always create a NEW PR. | **BLOCKED** |
| **DIAGNOSE BEFORE FIX** | Diagnose root cause first (inspect, measure, log). NEVER guess. Verify fix before reporting. | Manual |
| **PRODUCT DECISIONS** | When Patrick makes a UX/product decision, implement it. Technical objections only for data loss, security, or irreversibility. Record in `docs/decisions.md`. | Manual |
| **TEST BEFORE SUGGESTING** | NEVER tell user to do something without verifying it works. If you can't test, say so. | Manual |
| **NO RESET --HARD** | NEVER run `git reset --hard`. Destroyed uncommitted Bloomberg terminal work. Use `git merge` or `git rebase` to sync branches. If uncommitted changes exist, `git stash` first. No exceptions. | **BLOCKED** |

**If you're about to commit or touch main: STOP and verify these checkpoints first.**

---

## Git Flow

### Branching Strategy

```
develop (work here) → PR → main (production)
                      ↑
               NEVER reverse this
```

| Branch | Purpose | Protection |
|--------|---------|------------|
| `develop` | Working branch | None — commit directly |
| `main` | Production ONLY | PR required, CI must pass |

- **Feature branches** for: new services, architecture changes, multi-file refactors, big UI changes, multi-session work, 5+ files
- **Direct on develop** for: small fixes, tweaks, internal docs
- **NEVER** commit directly to main, merge to main via CLI, deploy without "deploy", or click "Update branch" on GitHub PR page

### Forbidden Operations (on develop)

| Operation | Why |
|-----------|-----|
| `git merge main` | Develop flows TO main only |
| `git pull origin main` | Pulls and merges main into develop |
| `git rebase main` | Rewrites develop history based on main |

If main and develop diverge, merge develop into main via PR — never the reverse.

### PR Rules

**Verification** — When asked to check a PR:
1. `git fetch origin` (ALWAYS fetch first)
2. `git log origin/main..develop --oneline` (ALWAYS origin/main, not local main)
3. `gh pr view <N> --json commits` to see what's in the PR
4. Report the delta — never just update PR title/body

**Merged PRs** — Once merged/closed, a PR is DEAD. After any `git push`:
1. Check: `gh pr list --head develop --base main --state open`
2. No open PR → create NEW one. NEVER reference old PR numbers without checking state.

Hooks: `merged_pr_guard.py` blocks edits to merged PRs. `post_push_pr_check.py` checks after every push.

### Pre-Commit Protocol

Before every commit, show Patrick:
1. `git status` — staged, unstaged, untracked
2. `git diff` — actual changes
3. `git log -3` — recent commits for style
4. Planned commit message
5. What will NOT happen (no main, no deploy, no PR)

Then **WAIT for explicit approval**. A question or comment resets the checkpoint — answer it, then wait again.

Also verify: claudeLog.md updated, all files staged, feature tested.

---

## WSL2 Claude Code Sandbox

WSL2 provides an isolated Linux environment for Claude Code sessions. See `infrastructure/wsl/CLAUDE.md` for setup contracts and environment-specific details.

**Environment variables:** App-specific variables are defined in `infrastructure/wsl/CLAUDE.md` and passed to companion repos during bootstrap. Claude-env itself has no app-specific environment requirements.

**Hooks:** Hooks run in WSL2 and may detect the environment via `/proc/version` for platform-specific behavior adjustments.

---

## Principles

| Principle | Description |
|-----------|-------------|
| **Rules are hard blocks** | Patrick's rules are HARD BLOCKS. Hooks must fail (non-zero), never warn-and-pass. |
| **Challenge me** | Push back against bad practices or security vulnerabilities. |
| **Admit limitations** | Never pretend capabilities you lack. Say so and suggest mitigations. |
| **UI matches implementation** | Never put placeholder text suggesting unbuilt functionality. |
| **Evaluate all options** | Before saying "no", consider all tools: Bash, PowerShell, web access, APIs, system commands. |
| **Do it yourself** | Work autonomously. Never ask user to do something you can do. Only escalate for commit/deploy approval or genuine capability gaps. |
| **Act on credentials** | When given API keys/passwords, use them directly — don't give instructions back. |
| **Questions require answers** | If asking "Ready to commit?" — STOP and wait. Never ask then immediately act. |
| **No feature regression** | Changes should never lose functionality. |
| **Fix problems immediately** | No technical debt. Fix deprecated code, broken things, suboptimal patterns now. |
| **Flag deprecated APIs** | Use current APIs in new code. Fix straightforward deprecations; flag complex ones. |
| **Design prototypes are contracts** | Implement EVERY effect in a prototype. See `research/DESIGN_IMPLEMENTATION_LESSONS.md`. |
| **PowerShell ONLY** | Bash tool runs actual bash. For Windows: `powershell.exe -Command "..."`. Never raw bash syntax. |
| **Prefer FOSS / winget** | MIT/Apache/BSD over proprietary. Lightweight, offline-capable. Use winget for installs. |
| **No paid services** | Never sign up for paid services on Patrick's behalf. |
| **No ad tech/tracking** | No advertising, tracking pixels, or data sharing with X/Meta. |
| **Cite sources** | When making recommendations, cite sources so Patrick can verify. |
| **Respect public APIs** | Rate limit (single-concurrency, 2s gap), cache in DB, polite User-Agent. |
| **Log sanitization** | ALL user strings in logs wrapped in sanitization wrappers where applicable. Enforced by hook. |
| **Cross-browser / local CSS** | Standard APIs and CSS only. Locally compiled CSS, CDN only for large libs with SRI hashes. |
| **Fetch before comparing** | ALWAYS `git fetch origin` first. Compare `origin/main` not local `main`. |
| **Validate doc links** | Run `python helpers/check_links.py --all` before committing doc changes. |
| **Audit the class** | When a bug is found as "we forgot X in location Y," immediately search for every other location where X might also be missing. Don't fix one instance — fix the class. |
| **Verify repo context** | Before writing files or committing to a repo other than the one open in the IDE, verify the target repo's current branch and confirm it's the correct destination. Don't let files end up in the wrong project. |
| **Preserve original media** | Never degrade user-uploaded images/media. Store originals at full quality. Use resized/compressed versions for display performance (thumbnails, previews), but always provide a way to view or download the original. |

---

## Session Protocol

### Starting ("hello!")
1. Read: `CLAUDE.md`, `sessionState.md`, `claudeLog.md`, `whileYouWereAway.md`, `docs/decisions.md`
2. If WYA has tasks, ask about them. Complete one step at a time.

### During
- **Checkpoints:** Save to `sessionState.md` after major tasks, every 10-15 exchanges, before complex work
- **Context efficiency:** Only load files actively needed. Exception: CLAUDE.md always loaded.
- **Plan hygiene:** Delete completed plan files. Verify git state before working from plans.
- **Between tasks:** Check Slack (`python helpers/slack_bot.py status`), review WYA, suggest 2-3 items.
- **Slack triggers:** Check after PR merges, multi-step tasks, idle moments, before reporting "done".
- **Post-compaction:** Track what info was lost, update docs with reusable context that survives compaction.

### Ending ("night!")
1. Update `sessionState.md`
2. Commit pending changes
3. Update `claudeLog.md`

---

## Coding Standards

- JavaScript/TypeScript: `camelCase` | Python: `snake_case` (PEP 8) | Bash: `snake_case` | Docs: GitHub-flavored Markdown
- **Testing:** Code compiling is NOT sufficient. Run tests before committing. Test external dependencies before integrating.
- **Script validation:** Bash scripts must be shellcheck-clean. Python scripts must pass linting (flake8 or ruff).

### Model Delegation

| Model | Use for |
|-------|---------|
| **Haiku** | Quick scripts, simple file ops, straightforward fixes, running tests |
| **Sonnet** | General development, coding, debugging (default) |
| **Opus** | Architecture, complex refactors, deep research, system design |

Run agents in parallel when possible.

---

## Communication

- **Research before asking** — search the web first, only ask Patrick if unclear
- **Correction vs inquiry** — if Patrick asks "Did you do X?", ask if it should be a guideline
- **Proactive updates** — add feedback-based rules to CLAUDE.md immediately when agreement is reached
- **Slack:** React ✅ to every message, mark `read: true` in `slack_inbox.json`, restart listener if disconnected

---

## File Management

- **CLAUDE.md backups:** Save as `claude_MMDDYYYY-N.md` before updating
- **Logging:** Log to `claudeLog.md` with date, description, result. Omit sensitive data.
- **Archives:** Source to `archive/`. Delete `__pycache__`, `node_modules`, `bin/`, `obj/`, logs, temp files.

---

## Security

- **Personal identifiers are secrets.** Personal email addresses, phone numbers, home addresses, and personal domains (e.g., `psford.com`) must be treated as credentials — never hardcoded in source files committed to public repos. Use `example.com` in defaults, documentation, and config templates. Real values belong in `.env` (gitignored) or environment variables only. Support/business emails created for a project are fine.
- Review SAST/DAST coverage when introducing new frameworks (SecurityCodeScan for C#, Bandit for Python)
- Hooks run automatically — if blocked, try to adjust; if stuck, ask Patrick

---

## Project Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Rules and shared knowledge for claude-env |
| `sessionState.md` | Current session context |
| `claudeLog.md` | Action log |
| `whileYouWereAway.md` | Task queue |
| `helpers/` | Python/PowerShell utilities (Slack, security, testing, helpers) |
| `infrastructure/wsl/CLAUDE.md` | WSL2 sandbox setup contracts and environment variables |
| `.claude/hooks/` | Git hooks enforcing code quality and repo hygiene |
| `.env` | API keys and secrets — not committed |

---

## Hooks and Plugin Management

Claude-env provides hooks that are imported and executed by companion app repos during bootstrap:

- `.claude/hooks/` — Pre-commit, pre-push, and CI hooks
- Hooks are shared read-only from claude-env
- Each companion repo (stock-analyzer, road-trip, etc.) has its own `.claude/config/` directory with local hooks

See Phase 6 bootstrap script for integration details.

---

## Next Steps

**Phase 6** creates the bootstrap script that will:
1. Clone claude-env into the target app repo
2. Symlink or copy hooks into app repo's `.claude/hooks/`
3. Configure environment variables for the specific app
4. Validate all hooks are present and executable
