Hi Claude,

This file will be used to keep track of rules, best practices, and all of the other details that will guide our work together. You should add additional entries and refer back to them as I give you feedback.

My background is a longtime financial services business analyst, who has programmed in Matlab and dabbled in Python, Ruby, and a few others. As we work together, my preferred languages for projects are Python, Typescript, HTML and CSS.

# guidelines

1. All documentation should be written in Github flavored Markdown.
2. Create new sections or subsections to this document as needed, but version history is important.
3. If you need additional tooling, let me know, and provide me with detailed options.
4. Math must be correct. If there is any doubt that you can provide an accurate result out to 5 decimal places of precision in a calculation you must let me know.
5. Challenge me. If I ask you to do something that is against best practices or could introduce a security vulnerabilty I need to know.
6. When suggesting a particular programming language or approach, give me a few alternatives as well, with arguments for the option you chose.
7. You don't have my credit card number, but even so - never sign me up for any paid service.
8. If you need logins to sites like Github, let me know, but make sure you give me detailed instructions so that you have access to the account. I'm not going to give you my passwords.
9. You will not ever act illegally.
10. Wherever possible, you will cite sources so I can understand the background of your suggestions.
11. When updating CLAUDE.md, save a versioned backup copy using the format `claude_MMDDYYYY-N.md` where N is the commit number for that day, incrementing with each commit (e.g., `claude_01132026-1.md` for the first commit, `claude_01132026-2.md` for the second commit, etc.).
12. Log terminal action summaries to `claudeLog.md`. Include date, action description, and result (success/failure). Omit sensitive data. If the file exceeds 1GB, archive it using the date convention (`claudeLog_MMDDYYYY.md`) and start a new `claudeLog.md`.
13. Naming conventions: use `camelCase` for JavaScript/TypeScript; use `snake_case` for Python (per PEP 8).
14. Session commands:
    - **"night!"** — Save state: update `sessionState.md` with current context, commit all changes
    - **"hello!"** — Restore state: read `CLAUDE.md`, `sessionState.md`, `claudeLog.md`, and `dependencies.md` to reload prior context
15. Test before completion: Always verify that UI and functional changes work as intended before reporting them as complete. For web interfaces:
    - Code compiling or importing successfully is **NOT sufficient** verification
    - Must actually open the browser and verify the feature renders and functions correctly
    - For interactive features (hover, click, etc.), must verify the interaction produces the expected result
    - If unable to directly verify browser behavior, explicitly state this limitation and ask the user to test
    - Never claim a UI feature is "complete" based solely on code analysis
16. Commit freely: No need to ask permission before committing changes. Commit as part of the normal workflow, as long as rollback capability is maintained via git history.
17. No feature regression: Updates should never result in loss of functionality. If a requested change would cause feature regression, clearly explain the tradeoffs. Code complexity should not be a limiting factor—write custom code to satisfy business requirements rather than sacrificing functionality. User requirements take priority.
18. Task file on startup: On session start ("hello!"), check `whileYouWereAway.md` for new tasks. If tasks exist, ask the user if they want to start working on them.
19. Enhancement tracking: Document enhancement requests and their status in `ROADMAP.md`. Keep this document updated as features are planned, in-progress, or completed.
20. Step-by-step evaluation: For multi-step tasks from `whileYouWereAway.md`, stop after completing each step to allow user evaluation before proceeding to the next.
21. Guideline adherence: Regularly refer back to these guidelines. If behavior deviates from guidelines, update them as needed to prevent future deviation.
22. Context window efficiency (hot/cold storage): Before reading files into context, evaluate whether the data is actually needed. Apply a hot/cold storage approach:
    - **Hot (load immediately):** Data actively needed for the current task
    - **Cold (fetch on demand):** Reference material that may not be needed
    - Do not read files "just in case" - fetch them when actually required
    - If data was loaded but not used, reconsider the loading pattern for future tasks
    - This applies to all projects, not just stock analyzer
    - **EXCEPTION - Rules files are sacrosanct:** Always load `CLAUDE.md` and similar rules/guidelines files into context. These established rules override efficiency concerns—they must be present to ensure consistent behavior across sessions.
23. Check the web before asking: When uncertain about syntax, best practices, or technical details, search the web first before asking the user. Only ask if web research doesn't provide a clear answer.
24. Local helper code over API calls: Write reusable local programs to accomplish repetitive tasks rather than making repeated API calls. Store these in `helpers/` folder.
    - **Unix philosophy:** Build small, modular programs that do one thing well and can be composed together
    - **Upfront investment:** Spend time building foundational tools that save effort long-term
    - **Examples:** Web scraping tools, data processors, automation scripts
    - **Output:** Prefer flat-file results that can be read without additional API calls
    - Always err on the side of building reusable infrastructure
25. Proactive Slack listener management: If the Slack listener is not receiving messages or appears disconnected, restart it without asking. Check inbox status and restart the listener proactively to maintain two-way communication.
26. Clarify correction vs inquiry: If the user asks "Did you do X?" and the answer is no, ask whether they would like this added as a guideline. The user may be inquiring or correcting—don't assume which.
27. Test end-to-end, not just startup: When implementing two-way communication or any system with input/output, verify the full round-trip works—not just that the service starts. For the Slack listener: send a test message, then confirm it appears in the inbox. A running process is not proof of functionality.
28. Redeploy after committing: See deployment rule D2.
29. Use PowerShell fully: When working in PowerShell, leverage its full functionality for local processing. Prefer local commands over API calls to minimize token usage.
30. Checkpoint system for graceful session ending: Save state periodically during long sessions to enable recovery if the session ends unexpectedly or approaches token limits.
    - **When to checkpoint:** After completing major tasks, every 10-15 exchanges, or before starting complex multi-step work
    - **How:** Run `python helpers/checkpoint.py save "description"` or manually update sessionState.md
    - **Headroom:** Reserve ~5,000-6,000 tokens for graceful exit (state save, commit, log update)
    - **Warning signs:** Tool output truncation, summarization occurring, very long conversation
    - **Graceful exit protocol:** Warn user, complete current atomic task, save checkpoint, commit, update log
31. Document scan/audit findings: When running security scans (SAST, DAST) or other audits, add findings to ROADMAP.md. Include issue description, severity, and recommended fix. This ensures nothing is forgotten and provides a clear remediation backlog.
32. Keep whileYouWereAway.md (WYA) updated: When completing tasks from WYA, mark them done immediately with a brief summary of what was accomplished. This keeps the task queue accurate and provides context for future sessions.
33. "As a user" statements: When the user starts a prompt with "as a user" (or similar phrasing), treat it as a functional requirement and add it to `docs/FUNCTIONAL_SPEC.md`. These are user stories that define expected behavior.
34. Building ≠ Running: See deployment rule D3.
35. Never overwrite plan files: When creating implementation plans, always create a NEW plan file rather than overwriting an existing one. Plan files outside of git-tracked directories cannot be recovered if overwritten.
36. Commit before overwriting: Before modifying or deleting any file, ensure the previous version is recoverable:
    - **Commit first:** If working in a git repo, commit current state before making destructive changes
    - **Check git status:** Verify uncommitted changes won't be lost
    - **For non-git files:** Create a backup copy before overwriting (e.g., `filename_backup_YYYYMMDD.ext`)
    - **Atomic operations:** When replacing file contents, prefer edit operations over full rewrites when possible
    - **Principle:** The user should always be able to recover any previous version of any file
37. Proactive guideline updates: When the user provides feedback, evaluate whether it should become a guideline. If the feedback would improve future results or prevent repeated issues, add it to CLAUDE.md without being asked. Use judgment—not every comment needs to be a rule, but patterns and corrections should be captured.
38. Test external services before integrating: When adding code that depends on an external web service, API, or URL:
    - **Verify the service is operational** before writing integration code (use WebFetch or equivalent)
    - **Check the response** is what you expect (correct content-type, valid data, no errors)
    - **Have a fallback plan** if the service is unreliable or goes down
    - **Never assume** a service works based on documentation or past experience—test it now
    - This applies to: CDNs, placeholder image services, APIs, webhooks, any external dependency
39. Slack message confirmation: When completing a task received via Slack, add a ✅ reaction to the original message to confirm completion. This provides visual feedback in the Slack channel.
40. Review security tools on new frameworks: Any time a new framework or language is introduced, review SAST and DAST tools to ensure adequate coverage. Add new scanners if needed (e.g., SecurityCodeScan for C#, Bandit for Python).
41. Keep specs updated — SAME COMMIT RULE: Spec updates MUST be included in the same commit as code changes, never as a follow-up commit.
    - **TECHNICAL_SPEC.md — ALWAYS update** for any code changes: new files, new dependencies, architecture changes, configuration changes, test additions, security updates, etc. This is the technical reference.
    - **FUNCTIONAL_SPEC.md — Update ONLY when user-facing behavior changes:** new features, UI changes, workflow changes, or requirement modifications. Internal refactoring, tests, and infrastructure don't require functional spec updates.
    - **Before running `git commit`:** Stage spec files alongside code files. If you're about to commit code without spec updates, STOP and update the specs first.
    - **Violation of this rule has happened repeatedly.** Do not commit code changes without the corresponding spec updates in the same commit.
42. Test before commit: When making functional changes, ensure the server is running and have the user verify the changes work as expected before committing. Do not commit untested code.
43. Web documentation sync: The Stock Analyzer documentation page (`wwwroot/docs/`) serves copies of CLAUDE.md, FUNCTIONAL_SPEC.md, and TECHNICAL_SPEC.md. These are automatically synced during `dotnet build` via MSBuild targets in StockAnalyzer.Api.csproj. After updating any of these source files, rebuild to sync the web copies. The source locations are:
    - `claudeProjects/CLAUDE.md` → `wwwroot/docs/CLAUDE.md`
    - `stock_analyzer_dotnet/docs/FUNCTIONAL_SPEC.md` → `wwwroot/docs/FUNCTIONAL_SPEC.md`
    - `stock_analyzer_dotnet/docs/TECHNICAL_SPEC.md` → `wwwroot/docs/TECHNICAL_SPEC.md`
44. Prefer FOSS tooling: When selecting libraries, tools, or dependencies, prefer well-supported Free and Open Source Software (FOSS) over proprietary alternatives. Prioritize:
    - Active maintenance and community support
    - Permissive licenses (MIT, Apache 2.0, BSD)
    - Lightweight solutions over heavy frameworks
    - Tools that work offline/locally when possible
    - Established projects over bleeding-edge experiments
45. Pre-commit spec check: Before committing any feature or enhancement, STOP and verify:
    - Does FUNCTIONAL_SPEC.md need updating? (user-facing changes)
    - Does TECHNICAL_SPEC.md need updating? (any code changes)
    - If either answer is yes, update specs BEFORE running `git commit`
    - **This is a mental checkpoint, not a post-commit cleanup task**
    - The commit message should describe what was built AND documented together
    - **Root cause of past violations:** Treating "commit" as end-of-task instead of treating "specs updated + committed" as end-of-task
    - **IMPORTANT:** When the user says "commit" or "go ahead and commit", this is shorthand for "complete the full commit workflow" — not a literal single `git commit` command. The full workflow includes: spec updates, claudeLog updates, staging all related files, then committing.
46. Archive source code, delete cruft: When retiring or reorganizing projects:
    - **Archive (preserve):** Source code files, configuration files, documentation that may have future reference value
    - **Delete (don't preserve):** Cache directories (`__pycache__`, `node_modules`, `bin/`, `obj/`), log files, temporary files, superseded documentation, old scan reports
    - **Move to `archive/` folder:** Retired projects should be archived, not deleted, in case code needs to be referenced later
    - **Consolidate infrastructure:** Shared helpers, configs, and tools should be moved to a common location, not duplicated

# deployment

Rules for deploying code changes to running services.

D1. Kill before deploy: Before starting a new version of a background service or listener:
    - **Identify running instances:** Check for existing processes running the same script/service
    - **Kill old processes:** Terminate all old instances before starting the new one
    - **Verify termination:** Confirm old processes are dead before proceeding
    - **Single instance principle:** Only one version of a service should run at a time (unless explicitly designed for multiple instances)
    - **Failure mode:** Multiple listeners = unpredictable behavior (old code may handle requests)

D2. Redeploy after committing: When code changes are committed to a running service:
    - Ask the user if the service should be restarted
    - A commit without redeployment leaves old code running
    - The new code only takes effect after the service is restarted
    - (Moved from guideline #28)

D3. Building ≠ Running: A successful build/compile does not mean a service is accessible:
    - **Verify the process is running:** Check if the port is listening
    - **Start the service if needed:** Either start it, or tell the user the command
    - **Test the endpoint:** Hit a health check to confirm the service responds
    - **Never claim "it's ready at localhost:XXXX"** based solely on a successful build
    - (Moved from guideline #34)

D4. Test end-to-end after deployment: After restarting a service:
    - **Verify functionality:** Don't assume the new code works because the process started
    - **Test the change:** Actually exercise the feature that was modified
    - **Check for regressions:** Ensure existing functionality still works
    - A running process is not proof of correct functionality

D5. Deployment checklist:
    1. Commit changes
    2. Kill old process(es)
    3. Start new process
    4. Verify process is running
    5. Test the specific change
    6. Test basic functionality (smoke test)

# known issues

## yfinance dividend yield data

**Issue:** The `dividendYield` field from yfinance can return inconsistent values. For example, AAPL showed 40% dividend yield when the actual value is ~0.4%.

**Cause:** yfinance sometimes returns dividend yield as a decimal (0.004 = 0.4%) and other times as a larger value that doesn't need multiplication. The data comes from Yahoo Finance and can be inconsistent.

**Fix (implemented):** In `stock_analysis/stock_analyzer.py`, the `get_stock_info()` function validates the dividend yield:

```python
# Validate dividend yield - yfinance can return inconsistent values
# Expected format: decimal (0.004 = 0.4%), but sometimes returns 100x higher
raw_yield = info.get("dividendYield", "N/A")
if isinstance(raw_yield, (int, float)):
    if raw_yield > 0.10:
        # Value > 10% is likely inflated by 100x, correct it
        dividend_yield = raw_yield / 100
    else:
        dividend_yield = raw_yield
else:
    dividend_yield = "N/A"
```

**Status:** Implemented 01/13/2026 - AAPL now correctly shows 0.40% dividend yield
