# Session State

_Last updated: 2026-08-22_

## Where things stand

| Repo | State |
|------|-------|
| claude-harness | `develop` @ `60a4cf3`, clean, deployed at that SHA via deploy-dashboard.sh. PRs #80–#108 merged across the session; #106 (develop -> main, the scaffolding phase) merged. |
| claude-env | `develop`, clean except this file + claudeLog.md. No code changes this session. |

## Waiting on Patrick

- **PR #109** (claude-harness develop -> main): the CH-149 delta that landed
  just after #106 merged. Merging it makes main whole.

## The store

- 165 tickets. Every story and epic closed except **CH-164 (Steer from the
  board)**, held open at Patrick's word ("leave it") as the home for future
  board-steering stories.
- CH-149 shipped and closed the phase: commit approvals ride the board
  (`ticket ask --audience patrick`), manual-AC ticks default unchecked and
  the board's Accept refuses unticked criteria. Proven live — both of its
  commits were approved from the board, and the accepting click exercised
  the enforcement it shipped.

## The real milestone (next session starts here)

The scaffolding phase is DONE. Patrick, 2026-08-22: "I need this
infrastructure to be working, so I can use it to make other software."
The next epic filed should be actual software, scoped via
psford-tickets:scoping-an-epic.

## Standing agreements made this session

- Two-surface rule: dashboard is Patrick's; CLI refusals must print what
  happened, the incident, and the exact way forward (memory: feedback_two_surface_rule).
- One story in flight; while anything is in_review/uat the only work is its
  review (memory: feedback_one_story_in_flight).
- The dashboard IS production: deploys only via deploy-dashboard.sh's smoke
  gate; restart = deploy (memory: feedback_dashboard_is_production).
- Gates are built only for failures that already cost real work; the scar
  lists (mutation_smoke MUTANTS) grow on postmortems only.
- UAT ticks are affirmative: unchecked by default, Accept demands them
  (CH-149 round 1, Patrick's nit — a pre-ticked box claims the looking
  for him).
