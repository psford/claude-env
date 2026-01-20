# While You Were Away

Scratchpad for quick notes, pending questions, and items to discuss next session.

**For feature requests:** Add to [ROADMAP.md](projects/stock-analyzer/ROADMAP.md) instead.

---

## Current Items

### Pending Tasks

- [ ] **Cloudflare IP allowlist** - Update App Service to only allow Cloudflare IPs. Security hardening.
- [ ] **About Us page** - Create page explaining what we do and our principles (no ad tech, no tracking, no data sharing with X/Meta).
- [ ] **Favicon from bird image** - Convert robin/fat bird image to vector and use as site favicon. Image at `slack_downloads/20260119_025039_robin_fat_bird.png`.
- [ ] **Image ML quality control** - Reject images where cat/dog face can't be reasonably cropped (bounding box too small or off-frame). Several images showing cropped-out faces.
- [ ] **CI dashboard** - Build dashboard to visualize CI runs and builds.
- [ ] **Brinson attribution analysis** - Major feature: Add Brinson-model attribution for mutual fund evaluation. Monthly holdings data. Requires significant planning before coding.

### Blog Ideas (for future dev blog)

- [ ] "LLMs are border collies" - analogy for working with AI assistants

### Recently Completed (sync with ROADMAP)

- [x] **Add favicon** - Complete set of favicons already in wwwroot (favicon.ico + multiple PNG sizes). **DONE**
- [x] **App Service migration** - Migrated from ACI to App Service B1. Quota check no longer needed. **DONE**
- [x] **Dark/light toggle in combined view** - Header with toggle is shared across all views. **DONE**
- [x] **Custom domain + SSL** - psfordtaurus.com configured via Cloudflare (free SSL). **DONE**
- [x] **Mobile responsiveness** - Hamburger menu + slide-in sidebar added (in develop, ready to deploy). **DONE**

---

## Version History

| Date | Change |
|------|--------|
| 01/19/2026 | Cleaned up: Removed obsolete App Service quota check (now on B1), marked favicon as done, verified dark mode toggle |
| 01/18/2026 | Added: Favicon, Cloudflare IP allowlist, About Us page, combined view theme toggle from Slack. Guidelines: winget preference, no ad tech. |
| 01/17/2026 | Added: Recurring check for App Service quota (pending increase for ACI → App Service migration) |
| 01/17/2026 | Cleaned up: Moved Azure deployment (#13) and user stories (#8) to ROADMAP.md. Removed 12 completed items. |

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
10. ~~Fork this project and recreate it all using C# and .Net.~~ **DONE** - projects/stock-analyzer is now the active project.
11. ~~Think about ways to gracefully end sessions near token limit.~~ **DONE** - Created helpers/checkpoint.py.
12. ~~Think about how we would implement a CI/CD Jenkins workflow.~~ **DONE** - GitHub Actions + Jenkins pipeline in place.
13. Switch hosting from Oracle to Azure. → **MIGRATED** to ROADMAP.md (High Priority) → **COMPLETED**

</details>
