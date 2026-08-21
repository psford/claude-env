# Session State

_Last updated: 2026-08-21_

## Where things stand

| Repo | State |
|------|-------|
| claude-harness | `develop` @ `bbf171e`, clean. PRs #80–#86 merged (CH-61 recovery + retro-mitigation epic CH-137). Gate green incl. new lint + mutation-smoke steps. Dashboard restarted on merged develop. |
| claude-env | `develop`, clean except this file + claudeLog.md. No code changes this session. |

## Waiting on Patrick

- **develop → main**: claude-harness develop is ~33 commits ahead of main with no open PR. Deploy-shaped decision, his call.

## What happened (2026-08-20/21)

The 3-day CH-61 thrash was recovered, retrospected, and answered with epic CH-137
(9 stories accepted, 2 cancelled with recorded verdicts). Full narrative:
`claude-harness/docs/retrospectives/2026-08-21-ch61-thrash-retro.md` and
`claude-harness/docs/process-notes-2026-08-20.md`.

## Open threads for next session

- **CH-149** — "steer things from the board": reparented OUT of CH-137
  (2026-08-21, Patrick's call) as the seed of its own future epic; needs a
  scoping conversation (psford-tickets:scoping-an-epic shape). Concrete gaps
  recorded on the ticket: in_review tickets show "Nothing is waiting on you"
  with no accept control; commit approvals surfacing on the board.
- ~~CH-150~~ — shipped (PR #87); epic CH-137 closed accepted 2026-08-21 on
  9 accepted + 2 cancelled children.
- **CH-75 / model tiers per role** — the still-undelivered original ask.
  Partially answered by Patrick: orchestrator = Haiku traffic cop (see memory
  `project_harness_role_model`).
- **CH-64** — dashboard SSE goes stale silently (bit Patrick again 2026-08-21).
- claude-env `docs/retrospectives/2026-04-03-map-poi-retro` still shows 14 open
  mitigations (pre-existing warning, untouched).

## Standing agreements made this session

- Two-surface rule: dashboard is Patrick's; CLI refusals must print what
  happened, the incident, and the exact way forward (memory: feedback_two_surface_rule).
- Gates are built only for failures that already cost real work; the scar lists
  (mutation_smoke MUTANTS) grow on postmortems only.
