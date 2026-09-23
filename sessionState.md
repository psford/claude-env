# Session State

_Last updated: 2026-09-22, end of night (the reply check live; the Jev trial able to start)_

## Where things stand, 2026-09-22

**Nothing in flight, and nothing waiting on Patrick.** Tonight's PRs are merged: claude-env #84 (the reply check) and claude-harness #166 and #167. The plugin cache serves 0.6.24.

**The reply check is live** as a Stop hook in `~/.claude/settings.json`, pointing at this checkout. It announces "reply NOT checked" on stderr whenever it cannot run, and never passes silently.

**Next, in order, when Patrick directs:**
1. The Jev trial: ship `jevfiles`, `jevgrep`, `jevread` and `jevask` from `claude-harness--jev/research/jev/tools/` onto every agent's PATH, logging through `jev`'s log. Then read the log after the first GLM dev run and show Patrick the delegate rows.
2. CH-224.137: the commit gate gives the release step and delivered review chores a home. Refile AC1 as a rule on the diff first. The reply-check manifest line waits in `stash@{0}` for it.

**Leftovers for Patrick to discard or keep**, all duplicates of reports already committed: untracked CSO report copies in the worktrees `claude-env--CE-2.55`, `claude-env--CE-2.56`, `claude-harness--CH-224.120`, `.122`, `.123` (also a stray `qa-verdict.json`) and `.127`.

**How to dispatch now:** devs on Flash (`glm-agent dev haiku`, stories filed at haiku) with a brief that names every change, test and edge case. Log a row in `~/.local/share/harness/tier-notes.md` for every dispatch. The CSO runs on Opus 5.5 or GLM-5.3, from the family that did not write the code.

## Where things stood, 2026-09-20

The board is the state of the work; this file only says what the board cannot.

**Nothing in flight.** Four stories accepted and merged today, one cancelled on measurement. Neither repo is pushed: claude-env `develop` is 10 commits ahead of main, claude-harness `develop` is 4. Both need a PR when you want them live.

**What merged.** CE-2.49 the memory health check (`helpers/memory_health_check.py`). CE-2.50 the worktree helper (`helpers/new-dev-worktree.sh`, creates and syncs in one step). CH-224.96 glm-agent resolving `--commit` against the caller's repo rather than claude-harness. CH-224.97 `ticket ac add --kind automated` requiring `--by`, which kills both the missing-verified_by class and the impossible-criterion class at filing time.

**CE-2.51 was cancelled, deliberately rather than parked.** A board-write guard scoring text against all 90 saved rules. Code sound, three criteria passing, 64 tests green — and against the real store it refused an innocuous two-line ticket on 19 rules, because its baselines were fitted on long chat messages and applied to short ticket text. A refit on 45 real tickets with 15 held out settled it: no threshold both stays quiet on good tickets and catches a bad one. Cancelled so the green suite cannot invite someone to wire it later. The measurement is attached to the ticket.

**Jev was measured, not adopted wholesale.** Two rounds in `/home/patrick/jev-lab` (untracked, outside any repo). `PLAN.md` there is the entry point and records every negative. The short version: in a code repo the free heuristic usually wins on average, and Jev earns its cost only where a cheap heuristic failing is expensive. Working: memory recall and health, semantic search within and across files, and a draft checker that works on CHAT messages but not on board text. Measured negative and not to be rebuilt: model-tier routing, effort estimation, diff-hunk ranking, a semantic index, Jev as a search loop, and the board-write gate above.

**Every nfl-stats ticket is accepted or cancelled.** claude-harness has CH-224.95 filed as backlog, in draft.

**nfl-stats is live at https://nfl.psford.com/** — a Cloudflare Worker serving static assets, deployed by merging a PR to `main`. Both release PRs merged today: #2 (the projection) and #3 (the deploy config).

**What shipped: NFL-6, the Start/Sit projection.** Players are ranked by a projection learned from 2016-2025, not by a blend of season averages.

- Part A (offline): `model_data.py` caches ten seasons; `projection.py` builds a player-game dataset whose inputs are provably pre-kickoff; `fit.py` fits a lasso per position with scikit-learn, holding out whole seasons; `backtest.py` grades it; `docs/projection-report.md` is the plain-language report Patrick read at the checkpoint.
- Part B (the page): `weekly_projection.py` applies the shipped weights as plain arithmetic, with a test proving the page modules import without scikit-learn. The page gained Proj (the default sort), Value (Proj minus Recent Form), Value picks per position, a projection log that grades itself once games are final, and a note.
- Held out on 2024-2025: beats Recent Form at every position on both measures. Against Blended PPG it wins average miss at QB, ties at WR and TE, is 0.07 points worse at RB, and orders players better everywhere. Patrick's checkpoint answer was one word: START.

**Deploying the site** is now: `.venv/bin/python refresh.py`, then `build_page.py`, commit the rebuilt `site/index.html`, PR to `main`, merge. What is live is whatever was last committed. The runbook is `nfl-stats/docs/DEPLOY.md`.

**Two harness fixes shipped** (psford/claude-harness#156): the queue no longer shows draft stories (CH-224.93), and an epic's accept is no longer blocked by `requires_uat`, which an epic could never satisfy (CH-224.94).

## Next, agreed with Patrick but not started

1. **Whether Jev retires Clyde — still open, and now better informed.** Patrick on Clyde: "a mid-to-ok idea in theory, and something of a disaster in practice"; nine dispatches, nine passes, nothing found, and it detached the main checkout twice. Jev cannot replace it outright — it has no hands, so it cannot exercise a feature. But Patrick's stated *original* intent for Clyde was the judgment half only ("were the test cases completed"), not the running half, which arrived later as an accretion in design 007. See `project_clyde_original_intent` and CH-224.92, which is 001's own position: checking an automated criterion is a command, not an agent.
2. **A shared Cloudflare first-connect runbook in claude-env**, written from what we actually saw in the dashboard today rather than from stale training data. The two things that bit us: the repo picker only lists repos the Cloudflare GitHub App can access (fix at github.com/settings/installations, not in Cloudflare), and the production branch comes from the repo's default branch, which had to be flipped from `develop` to `main`.
3. **Patrick's coworker is reviewing the site**, so feedback may arrive.

## Orientation, not hand-off

Patrick: **"the board should be the state of the work."** A new session orients
from the ticket stores (`ticket list` per repo), not from this file. Memories
carry the behavioral rules; this file only points.

## Facts a fresh session needs fast

- **omni-map is LIVE**: https://omni.psford.com (Cloudflare Worker, merge to
  main = deploy, suite runs in the build container). Azure backend
  func-omnimap-prod (GoMOFS relay + hourly NDBC snapshot blob). Specs:
  docs/SPEC-FUNCTIONAL.md / SPEC-TECHNICAL.md; runbooks: docs/DEPLOY.md /
  DEPLOY-API.md.
- **Before any omni-map push**: run the suite prod-env-shaped (VITE_API_BASE +
  VITE_SNAPSHOT_BASE set) AND remember every develop push fires a metered
  Cloudflare build — batch to release time, PRs via `ticket release` only.
  nfl-stats does NOT have this cost: it has no build step in Cloudflare.
- **az CLI on this box is logged in as PATRICK** (his provisioning login), not
  the photo-portfolio SP. Restore before photo-portfolio Azure work.
- **Zero trust / TNO** is in the shared core: no agent-usable hook bypasses
  exist or will; a block means satisfy-or-surface.
- The PR-state hook's "N unmerged commits" line is stale without a fetch;
  verify with `git fetch` + `git log origin/main..origin/develop` before
  believing it either way.
- **QA's cost** was the open question (5-minute dispatch budget, QA at sonnet).
  CH-224.38 (judge the delta, not the branch) and CH-224.40 (QA gates the
  release, not every ticket) are filed and are Patrick's call, since each
  loosens a control on the dev. Both may be overtaken by the approvals rework.
- Open threads by board: omni-map OM-26.5/26.7 (source ideas), OM-31.2/31.3
  (EV probe-from-Azure, lightning licensing-first); claude-harness CH-224.95
  (tests that read the ambient model provider); the release-ticket process is
  still Patrick's open ask; session-log commits still need a lane through the
  ticket commit guard.
