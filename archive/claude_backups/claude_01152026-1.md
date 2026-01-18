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
28. Redeploy after committing: When code changes are committed, ask the user if running services should be restarted to deploy the new code. A commit without redeployment leaves old code running.
29. Use PowerShell fully: When working in PowerShell, leverage its full functionality for local processing. Prefer local commands over API calls to minimize token usage.

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
