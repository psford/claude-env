# While You Were Away

Scratchpad for quick notes, pending questions, and items to discuss next session.

**For feature requests:** Add to [ROADMAP.md](stock_analyzer_dotnet/ROADMAP.md) instead.

---

## Current Items

*(Empty - nothing pending)*

---

## Version History

| Date | Change |
|------|--------|
| 01/17/2026 | Cleaned up: Moved Azure deployment (#13) and user stories (#8) to ROADMAP.md. Removed 12 completed items. |
| 01/16/2026 | Added: CI/CD Jenkins task (#12), Chocolatey preference |
| 01/15/2026 | Added: Slack integration (#4), checkpoint system (#11) |
| 01/14/2026 | Created: Initial task list with security scanning, context efficiency, remote communication |

---

## Archived Items (01/17/2026)

<details>
<summary>Click to expand completed/migrated items</summary>

1. ~~Add a future enhancement request for a static analyzer for code security.~~ **DONE** - Installed Bandit, created helpers/security_scan.py.
2. ~~Add a new guideline to evaluate whether or not you are really using the information that is read into the context window.~~ **DONE** - Added as guideline #22.
3. ~~Another guideline is to write local code wherever possible to prevent unneeded calls to Claude cloud.~~ **DONE** - Added as guideline #24.
4. ~~I won't always be home at this PC - please evaluate ways that you could communicate with me remotely.~~ **DONE** - Set up Slack integration.
5. ~~Look through your dependencies and see if rules.md is referenced anywhere.~~ **DONE** - File was empty, deleted.
6. ~~Give me suggestions on how we could add dynamic analysis security tools to our SDLC.~~ **DONE** - Installed OWASP ZAP, created helpers/zap_scan.py.
7. ~~Any time I start a prompt with "as a user" add that to the functional requirements.~~ **DONE** - Added as guideline #33.
8. Review the roadmap and propose user stories. → **MIGRATED** to ROADMAP.md (Medium Priority)
9. ~~Let's also start archiving log files.~~ **DONE** - Created helpers/archive_logs.py.
10. ~~Fork this project and recreate it all using C# and .Net.~~ **DONE** - stock_analyzer_dotnet is now the active project.
11. ~~Think about ways to gracefully end sessions near token limit.~~ **DONE** - Created helpers/checkpoint.py.
12. ~~Think about how we would implement a CI/CD Jenkins workflow.~~ **DONE** - GitHub Actions + Jenkins pipeline in place.
13. Switch hosting from Oracle to Azure. → **MIGRATED** to ROADMAP.md (High Priority)

</details>
