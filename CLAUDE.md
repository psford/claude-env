# CLAUDE.md

Instructions and shared knowledge for Claude Code sessions.

---

## CRITICAL CHECKPOINTS (READ FIRST)

These rules are enforced by Claude Code hooks. Violations will be blocked automatically.

| Checkpoint | Rule | Enforcement |
|------------|------|-------------|
| **COMMITS** | Show status → diff → log → message → WAIT for explicit approval ("ok", "commit", "go ahead") | Hook reminds; manual approval required |
| **MAIN BRANCH** | NEVER commit, merge, push --force, or rebase on main | **BLOCKED by hook** |
| **REVERSE MERGE** | NEVER merge main INTO develop (flow is develop → main only) | **BLOCKED by hook** |
| **PR MERGE** | Patrick merges via GitHub web only - NEVER use `gh pr merge` | **BLOCKED by hook** |
| **DEPLOY** | Only when Patrick says "deploy" + pre-deploy checklist complete | Hook reminds; manual approval required |
| **SPECS** | Update TECHNICAL_SPEC.md AS you code, stage with code commits | Pre-commit hook warns |
| **QUESTIONS ≠ APPROVAL** | If user asks a question, answer and wait - a question is NOT implicit approval | Manual discipline |

**If you're about to commit, deploy, or touch main: STOP and verify these checkpoints first.**

---

## About

**User:** Patrick - financial services business analyst background, experience with Matlab, Python, Ruby.

**Preferred languages:** Python, TypeScript, HTML, CSS, C# (.NET)

**Active project:** Stock Analyzer (.NET) - `projects/stock-analyzer/`

---

## HARD STOPS

**Never proceed without explicit user approval for these actions:**

| Action | Required Approval |
|--------|-------------------|
| **Commits** | Show status, diff, log, planned message → wait for "ok", "commit", or similar explicit approval |
| **Merges to main** | Patrick must approve and merge via GitHub web interface |
| **Deployments** | Patrick must say "deploy" |
| **Destructive git operations** | `git reset --hard`, `git push --force`, etc. require explicit approval |

## PR VERIFICATION PROTOCOL (MANDATORY)

**When asked to verify or check a PR:**

This is a HARD RULE that cannot be skipped. When Patrick says anything like "this PR does not look current" or asks about PR status:

1. **RUN THE COMPARISON** - Execute `git log main..develop --oneline` to get commits on develop not in main
2. **CHECK THE PR** - Use `gh pr view <number> --json commits` or check GitHub to see what commits are IN the PR
3. **COMPARE EXPLICITLY** - List which commits are missing from the PR
4. **REPORT FINDINGS** - Tell Patrick exactly what's missing

**What went wrong (2026-01-24):** When Patrick said "this PR does not look current," I only updated the PR title/body text without verifying the commits. The PR had 2 commits but develop had 13. This caused a production deployment without the required endpoints, wasting significant time.

**The correct response to "this PR does not look current":**
```powershell
# 1. Get commits on develop not in main
git log main..develop --oneline

# 2. Compare against PR commits
gh pr view 65 --json commits --jq '.commits[].oid[:7]'

# 3. Report the delta
```

**NEVER** just update PR title/body and claim it's fixed. The commits are what matter, not the description.

**The "questions require answers" rule applies here:** If Patrick responds with a question, comment, or any message that isn't explicit approval, that resets the checkpoint. Answer the question, then re-confirm readiness if needed. **Do not treat a question as implicit approval to proceed.**

## FORBIDDEN GIT OPERATIONS

**These operations are NEVER allowed, regardless of context:**

| Operation | Reason |
|-----------|--------|
| `git merge main` (on develop) | Corrupts git flow - develop flows TO main, never reverse |
| `git pull origin main` (on develop) | Same as above - pulls and merges main into develop |
| `git rebase main` (on develop) | Rewrites develop history based on main |
| Any merge FROM main INTO develop | The direction is always: develop → main via PR |

**Correct git flow:**
```
develop (work here) → PR → main (production)
                     ↑
              NEVER reverse this
```

If main and develop diverge, the solution is to merge develop into main (via PR), NOT to merge main into develop. A pre-merge hook exists to block this locally.

---

## Principles

These always apply, regardless of task.

| Principle | Description |
|-----------|-------------|
| **Challenge me** | If I ask for something against best practices or introducing security vulnerabilities, push back. |
| **Admit limitations** | If asked to do something I cannot actually do (e.g., "verify the UI looks correct" when I can't see rendered output), say so immediately and suggest mitigations. Never pretend to have capabilities I lack. |
| **Evaluate all options** | When asked "can you do X?", evaluate ALL tools at your disposal before answering. You have Bash, PowerShell, file operations, web access, etc. Don't reflexively say "no" without considering whether system commands, APIs, or tools could accomplish the task. Play a sound? `[System.Media.SoundPlayer]`. Open a browser? `Start-Process`. Send an email? PowerShell can do that. Think before declining. |
| **No illegal actions** | Never act illegally, period. |
| **No paid services** | Never sign up for paid services on my behalf. |
| **Cite sources** | When making recommendations, cite sources so I can verify. |
| **Offer alternatives** | When suggesting a language/approach, provide alternatives with tradeoffs. |
| **Prefer FOSS** | Choose well-supported open source (MIT, Apache 2.0, BSD) over proprietary. Prefer lightweight, offline-capable, established tools. |
| **Use winget** | For Windows app installations, prefer winget as the package manager. Fall back to Chocolatey if winget fails or lacks the package. |
| **PowerShell ONLY** | On Windows, ALWAYS use PowerShell for command-line operations. The Bash tool executes `/usr/bin/bash` (actual bash), NOT PowerShell. To run PowerShell commands, you MUST invoke PowerShell via bash like this: `powershell.exe -Command "Your-PowerShell-Command"`. Use PowerShell for: git, dotnet, file operations, process management (Stop-Process, Get-Process), environment variables, and all Windows system commands. NEVER use raw bash syntax (grep, awk, etc.) - always wrap PowerShell in powershell.exe. |
| **Azure CLI path** | Azure CLI is not in PATH. Always use full path: `& 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd'` |
| **No ad tech/tracking** | Never integrate advertising technology, tracking pixels, analytics that share data externally, or any data sharing with X (Twitter) or Meta. |
| **Math precision** | If uncertain about calculation accuracy to 5 decimal places, say so. |
| **No feature regression** | Changes should never lose functionality. If unavoidable, explain tradeoffs clearly. |
| **Minimize yak-shaving** | Work autonomously whenever possible. Create accounts, store passwords securely, build scaffolding without asking for direction. Don't ask for help on tasks you can figure out yourself. |
| **Act on credentials** | When given API keys, passwords, or other credentials, use them directly to complete the task. Don't provide instructions for the user to do it themselves - do it. |
| **Update specs proactively** | When implementing features, always update TECHNICAL_SPEC.md, ROADMAP.md, and other docs as part of the work - not as an afterthought. Don't wait to be reminded. |
| **PR-to-production** | Work directly on develop. PRs required only for main (production). Never commit directly to main. Never merge to main without Patrick's explicit approval. |
| **GitHub best practices** | Follow GitHub conventions: README.md and LICENSE at repo root, CONTRIBUTING.md for contribution guidelines, .github/ for templates and workflows. Use standard file names (README.md not readme.txt). |
| **README from day one** | Create README.md when starting any project and update it as work progresses. These are for Claude's continuity across compaction cycles - capture: purpose, file structure, how it works, build/install instructions, key technical decisions, and details that would otherwise be lost. When pushing to GitHub, the audience shifts to external users and may need rewriting. |
| **Validate doc links** | Before committing documentation changes, run `python helpers/check_links.py --all` to verify all markdown links resolve. Broken links are unacceptable. |
| **Version new behaviors** | When adding significant new functionality that changes core behavior (not just bug fixes), don't overwrite the existing working version. Ask first, or create a new version (bump version number, use feature flags, separate files, etc.). Working code that's already deployed/signed should be preserved. |
| **Cross-browser compatibility** | Strive for compatibility across browsers. Avoid tech exclusive to WebKit, Chromium, Gecko, or other engine-specific features. Use standard, widely-supported APIs and CSS. This applies to browser extensions, web apps, and any client-side code. |
| **Local CSS over CDN** | Always use locally compiled CSS (e.g., Tailwind built to `wwwroot/css/styles.css`) instead of CDN links. This avoids CSP issues, works offline, and ensures consistent styling. CDN scripts are acceptable only for large libraries with SRI hashes (e.g., Plotly.js). |
| **Questions require answers** | If I ask a question like "Ready to commit?" or "Want me to proceed?", STOP and wait for the user's response. Don't ask rhetorical questions then immediately act. Either act without asking, or ask and wait - never both. |
| **Fix problems immediately** | Avoid technical debt whenever possible. Fix problems as we find them, don't wait for later. Deprecated code in the codebase is a vulnerability. If something is broken, outdated, or suboptimal and we notice it, address it now rather than adding it to a backlog. |

---

## Session Protocol

### Starting a Session ("hello!")

When I say "hello!" at the start of a session:

1. Read these files to restore context:
   - `CLAUDE.md` (this file)
   - `sessionState.md` (where we left off)
   - `claudeLog.md` (recent actions)
   - `whileYouWereAway.md` (pending tasks)

2. If `whileYouWereAway.md` has tasks, ask if I want to work on them.

3. For multi-step WYA tasks, complete one step at a time and wait for my evaluation.

### During a Session

**Checkpoints** - Save state periodically to enable recovery:
- When: After major tasks, every 10-15 exchanges, before complex work
- How: Update `sessionState.md` or run `python helpers/checkpoint.py save "description"`
- Reserve ~5,000-6,000 tokens for graceful exit
- Warning signs: Output truncation, summarization, very long conversation

**Post-compaction learning** - After each context compaction:
1. Start a running list of questions about the prior session that were likely lost
2. At ~90% context usage, review those questions before next compaction
3. Identify patterns: What information keeps getting lost? What would have helped?
4. Update CLAUDE.md or project docs with reusable context that survives compaction
5. This continuous interrogation of gaps improves future session continuity

**Context efficiency** - Don't load files "just in case":
- Hot (load now): Data actively needed for current task
- Cold (fetch later): Reference material that might not be needed
- Exception: Always load CLAUDE.md - rules files are sacrosanct

**Plan and todo hygiene** - Keep state files current:
- When completing a feature from a plan file, DELETE the plan file (not archive - delete)
- When completing a task, immediately mark it done in todos/whileYouWereAway.md
- At session start, check for stale plan files in `~/.claude/plans/` and clean up completed ones
- If a plan exists but work is already done (check git log), delete the plan
- Never work from stale plans - verify actual git state first

**Between tasks** - When a task is complete or sitting idle:
1. **CHECK SLACK FIRST** - This is mandatory, not optional. Run `python helpers/slack_bot.py status` and read `slack_inbox.json` for unread messages.
2. Review `whileYouWereAway.md` for pending items
3. Check `ROADMAP.md` for items that could be progressed
4. Suggest 2-3 things to work on (with brief rationale)
5. Don't just wait - be proactive about finding productive work

**Slack check triggers** - Check Slack immediately after:
- Completing any deployment (localhost or production)
- Merging a PR
- Finishing a multi-step task
- Any idle moment where you're waiting for user input
- Before reporting "task complete" to the user

If Slack hasn't been checked in the current session and you're about to say "done" or "complete", check it first.

### Ending a Session ("night!")

When I say "night!":

1. Update `sessionState.md` with current context
2. Commit all pending changes
3. Update `claudeLog.md`

---

## Development Workflow

### Branching Strategy (MANDATORY)

We use a **PR-to-production** workflow. Development happens freely on `develop`, but production requires PR review.

```
develop (work here) → (user says "deploy") → PR to main → Production
```

| Branch | Purpose | Protection |
|--------|---------|------------|
| `develop` | Working branch for iteration. | None - commit directly |
| `main` | Production-ready code ONLY. | PR required, CI must pass, enforce admins |

**Development Workflow:**

1. **For significant features/architecture changes:** Use a feature branch
   ```bash
   git checkout develop && git pull
   git checkout -b feature/descriptive-name
   # make changes, commit incrementally
   git push origin feature/descriptive-name
   # merge to develop after testing (or create PR if preferred)
   ```

2. **For small fixes/tweaks:** Work directly on develop
   ```bash
   git checkout develop && git pull
   # make changes
   git add . && git commit -m "Description"
   git push origin develop
   ```

3. **For code changes:** Rebuild and test on localhost
   - Restart server: "Ready for testing at localhost:5000"

4. **For internal docs** (ROADMAP.md, whileYouWereAway.md, claudeLog.md):
   - Commit directly to develop - no PR needed

**When to use feature branches:**
- Adding new services or providers
- Architectural changes (new interfaces, DI restructuring)
- Multi-file refactors
- Anything that might need rollback as a unit

**Production Deployment (only when Patrick says "deploy"):**

1. Create PR from develop to main:
   ```bash
   gh pr create --title "Release: description" --body "..." --base main --head develop
   ```

2. Wait for CI, ask Patrick for approval

3. On approval, merge and trigger deploy workflow

**CRITICAL RULES:**
- **NEVER** commit directly to main - PRs only, no exceptions
- **NEVER** merge to main via CLI (gh pr merge, git merge) - use GitHub web interface only
- **NEVER** merge to main without Patrick's explicit approval
- **NEVER** deploy without Patrick saying "deploy"
- **NEVER** click "Update branch" on GitHub PR page - this merges main into develop (forbidden reverse merge)

The `develop` branch is for iteration. The `main` branch is sacred - it represents production code and requires formal process every time. Patrick will merge PRs to main through GitHub's web interface.

**Production Deploy:**
- Go to GitHub Actions → "Deploy to Azure Production"
- Click "Run workflow"
- Type `deploy` to confirm, provide reason
- Workflow builds, tests, and deploys to https://psfordtaurus.com

**CRITICAL - Pre-Deploy Checklist:**
Before ANY deployment to production:
1. ✅ Show Patrick the Bicep file (`infrastructure/azure/main.bicep`) for review
2. ✅ TECHNICAL_SPEC.md updated with all code changes
3. ✅ FUNCTIONAL_SPEC.md updated if user-facing changes
3. ✅ Docs updated in /docs folder (GitHub Pages serves them automatically)
4. ✅ Version history updated in specs
5. ✅ Security scans passed (CI checks)
6. ✅ User has tested on localhost and approved

**Never deploy to production without updating specs first.** This is a hard rule.

**Rollback:** See `projects/stock-analyzer/docs/RUNBOOK.md`

### Model Delegation Strategy

**Working model: Sonnet (default)** - Balanced for general development, coding, debugging

**Delegate to Haiku for:**
- Quick scripts (PowerShell, Python helpers)
- Simple file operations (git status, file reads)
- Straightforward bug fixes
- Running tests or builds
- Any task that's fast and doesn't require deep reasoning

**Delegate to Opus for:**
- Architecture decisions and planning
- Complex multi-file refactors
- Research and deep analysis
- Designing new features or systems
- Any task requiring "deep thinking"

**Usage:**
```
Task(subagent_type="general-purpose", model="haiku", prompt="...")
Task(subagent_type="Plan", model="opus", prompt="...")
Task(subagent_type="Explore", model="opus", prompt="...")
```

Run agents in parallel when possible - Haiku can run tests while Sonnet codes, or Opus can plan next feature while Sonnet finishes current work.

### Planning Phase

- For non-trivial tasks, use plan mode to design approach before coding
- When uncertain about requirements, research the web first, then ask me if still unclear
- Treat "as a user..." statements as functional requirements - add to `FUNCTIONAL_SPEC.md`

### Coding Phase

**Standards:**
- JavaScript/TypeScript: `camelCase`
- Python: `snake_case` (PEP 8)
- Documentation: GitHub-flavored Markdown

**Testing requirements:**
- Code compiling is NOT sufficient verification
- For UI changes: Use Playwright (`helpers/ui_test.py`) to verify:
  - `smoke` - Page loads without JS errors
  - `verify` - Required elements exist and are visible
  - `screenshot` - Capture visual state for review
- **For UI changes affecting layout/CSS:** Run responsive tests at all three viewport sizes BEFORE committing:
  ```powershell
  python helpers/responsive_test.py http://localhost:5000/<page> --prefix <name>
  ```
  - Mobile (390x844) - iPhone size
  - Tablet (768x1024) - iPad portrait
  - Desktop (1400x900) - Standard laptop
  - Review screenshots to verify layout works at each size
  - This is MANDATORY for any HTML/CSS changes - do not commit until responsive tests pass
- For interactive features: Verify the interaction produces expected results
- For services: Test the full round-trip, not just that it starts
- If unable to verify directly, say so and ask me to test

**External dependencies:**
- Before integrating any external service/API/CDN, verify it's operational
- Check the response is what you expect
- Have a fallback plan if unreliable
- Never assume a service works - test it now

**Spec updates - do them incrementally:**
- Update specs AS you write code, not after
- Don't batch spec updates at end of task - that leads to forgotten details
- Each code commit should include its corresponding spec changes
- If adding a new file/service/endpoint, update TECHNICAL_SPEC.md before moving on

### Pre-Commit Checklist

**Before every commit, STOP and show Patrick:**

1. **`git status`** - what's staged, unstaged, untracked
2. **`git diff`** - the actual changes being committed
3. **`git log -3`** - recent commits for message style consistency
4. **Planned commit message**
5. **What will NOT happen** (e.g., "will not touch main, deploy, or create PR")

Then **wait for explicit approval** ("ok", "commit", "go ahead", etc.) before executing.

**CRITICAL:** If Patrick responds with a question or comment instead of approval, that is NOT approval. Answer the question, then wait again. The commit happens ONLY after unambiguous approval - never after answering a question.

**Also verify before showing:**

1. **Specs updated?**
   - `TECHNICAL_SPEC.md` - update for ANY code changes (files, deps, architecture, config, tests)
   - `FUNCTIONAL_SPEC.md` - update ONLY for user-facing changes (features, UI, workflows)
   - Stage specs WITH code - same commit, not follow-up

2. **Log updated?**
   - Add entry to `claudeLog.md`

3. **All files staged?**
   - Check `git status` before committing

4. **Tested?**
   - Server should be running
   - Feature should be verified working

Commit message should describe what was built AND documented.

### Post-Commit / Deployment

**D1. Kill before deploy**
- Check for existing processes of the service
- Kill old instances before starting new
- Verify termination before proceeding

**D2. Redeploy after committing**
- A commit doesn't restart running services
- Ask if I want to restart after committing service changes

**D3. Building ≠ Running**
- Successful build doesn't mean service is accessible
- Verify process is running and port is listening
- Hit health check to confirm
- Never claim "ready at localhost:X" based solely on build success

**D4. Test after deployment**
- Don't assume new code works because process started
- Exercise the modified feature
- Check for regressions

**D5. Deployment checklist**
1. Commit changes
2. Kill old process(es)
3. Start new process
4. Verify process running
5. Test the specific change
6. Smoke test basic functionality

---

## Communication

**Research before asking** - Search the web first for syntax, best practices, technical details. Only ask me if research doesn't provide a clear answer.

**Correction vs inquiry** - If I ask "Did you do X?" and the answer is no, ask whether I want it added as a guideline. I may be inquiring or correcting - don't assume which.

**Proactive guideline updates** - When I give feedback that would improve future results or prevent repeated issues, add it to this file without being asked. Not every comment needs a rule, but patterns and corrections should be captured. **Critical timing**: Update CLAUDE.md in the same response where agreement is reached - not later when the mistake repeats. If we agree "use X approach going forward," add it immediately, not after violating it.

**Slack integration:**
- Proactively restart the Slack listener if it appears disconnected
- Add ✅ reaction to EVERY Slack message when acknowledged (not just when completed)
- Mark message as `read: true` in `slack_inbox.json` after reacting
- Keep `slack_inbox.json` and `slack_last_sync.txt` at project root

---

## File Management

**Version control:**
- Commit freely as part of normal workflow - no need to ask permission
- Before overwriting any file, ensure previous version is recoverable (commit first, or backup)
- Never overwrite plan files - create new ones instead

**CLAUDE.md backups:**
- Before updating this file, save backup as `claude_MMDDYYYY-N.md`
- N = commit number for that day (1, 2, 3...)

**Logging:**
- Log actions to `claudeLog.md` with date, description, result (success/failure)
- Omit sensitive data
- If file exceeds 1GB, archive as `claudeLog_MMDDYYYY.md` and start fresh

**Archiving projects:**
- Archive source code to `archive/` folder (preserve for reference)
- Delete cruft: `__pycache__`, `node_modules`, `bin/`, `obj/`, logs, temp files
- Consolidate shared helpers/configs to common location

---

## Security

**Scanning:**
- When introducing new frameworks/languages, review SAST/DAST coverage
- Add appropriate scanners (SecurityCodeScan for C#, Bandit for Python)
- Document scan findings in `ROADMAP.md` with severity and recommended fix

**Pre-commit hooks:**
- Hooks run automatically on commit
- If blocked by a hook, determine if you can adjust; if not, ask me to check hook configuration

---

## Project Files Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | This file - rules and shared knowledge |
| `sessionState.md` | Current session context for continuity |
| `claudeLog.md` | Action log with dates and outcomes |
| `whileYouWereAway.md` | Task queue for async work |
| `ROADMAP.md` | Feature roadmap (in `projects/stock-analyzer/`) |
| `FUNCTIONAL_SPEC.md` | User-facing requirements (in `projects/stock-analyzer/docs/`) |
| `TECHNICAL_SPEC.md` | Technical implementation details (in `projects/stock-analyzer/docs/`) |
| `helpers/` | Reusable Python scripts (Slack, security, checkpoints, UI testing, speech-to-text) |
| `.env` | API keys (Slack tokens, Finnhub) - not committed |

---

## Stock Analyzer Specific

**Web documentation:**
Documentation is served from GitHub Pages at https://psford.github.io/claudeProjects/. The app's /docs.html fetches markdown files from there, allowing doc updates without container rebuilds.

| Source | GitHub Pages URL |
|--------|------------------|
| `docs/FUNCTIONAL_SPEC.md` | `https://psford.github.io/claudeProjects/FUNCTIONAL_SPEC.md` |
| `docs/TECHNICAL_SPEC.md` | `https://psford.github.io/claudeProjects/TECHNICAL_SPEC.md` |
| `docs/SECURITY_OVERVIEW.md` | `https://psford.github.io/claudeProjects/SECURITY_OVERVIEW.md` |

To update production docs: Push changes to main branch. GitHub Pages deploys automatically.

**Version management:**
When bumping the version in ROADMAP.md (e.g., adding a new `**v2.X**` entry), also update the footer version in `wwwroot/index.html`. The footer displays the user-facing version number.

**Feature conventions:**

| Pattern | Components |
|---------|------------|
| **±5% Significant Move Markers** | When adding this feature to any chart, include the complete package: (1) Triangle markers on chart for days with ≥5% change, (2) Toggle checkbox to show/hide markers, (3) Wikipedia-style hover cards on marker hover, (4) Cat/dog image toggle, (5) News content in hover card (source varies by context - stock-specific news for individual stocks, market news for portfolios). |

---

## Deprecated / Archived

**Python stock_analysis project** - Archived to `archive/stock_analysis_python/`. The .NET version is now the sole active implementation.

**yfinance dividend yield issue** - Applied to archived Python code. The .NET version uses a different data source.
