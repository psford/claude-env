---
name: todo-sync
description: How the cross-machine todo tracker works — GitHub Issues mirror session todos; adopt tracked items, complete them to close issues, delete only tidies the session.
---

# Cross-machine todo tracker (GitHub Issues bridge)

Open `todo`-labeled issues in `psford/claude-env` are the shared,
machine-spanning todo store. At session start the `todo-restore` hook
injects the open tracked todos into context. Two hooks keep the tracker
and session todos aligned automatically; you never call `gh` for this.

## Working tracked todos

- **Adopt** a tracked todo you will work this session by calling
  `todo_create` with the same title — the sync hook dedupes against the
  tracker, so no duplicate issue is created.
- **Complete** the session todo when done (`todo_complete`) — that closes
  the tracked issue. This is the real outcome; do it for adopted items too.
- **Delete** only removes the session todo. If the item was adopted from
  the tracker (created by an earlier or other session/machine), the issue
  intentionally stays open — deletion is session tidying, not withdrawal.
  Only the session that created an issue closes it on delete.
- Titles are the join key: keep adopted titles identical to the tracked
  titles, and avoid creating same-titled todos for different work.
  Matching is normalized — whitespace and trailing punctuation are
  ignored — so a retyped title still adopts the tracked issue.
- Sync outcomes are not silent: filed / deduped / failed notices surface
  in your next turn as a system-reminder (todo-relay.sh); full history is
  in ~/.local/share/polytoken/todo-sync.log.

## Hygiene

- Descriptions on `todo_create` become the issue body — write them for the
  other machine (context, acceptance, pointers), not for this session only.
- A capped list (`(+N more …)`) means the backlog is long: prefer finishing
  tracked work over filing new todos.
- Sync failures never disturb the session; they append to
  `~/.local/share/polytoken/todo-sync.log` for later inspection.
