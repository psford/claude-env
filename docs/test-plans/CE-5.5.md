# CE-5.5 — a dangling link is caught by a machine

`sync-claude-md.sh --check` already detects all three broken shapes. Nothing
runs it. This story is about where it fires, so the plan is mostly about the
firing, not the detection.

## The case that is actually new

The check must run without anyone invoking it. So the test cannot be "run the
check and see it fail" — that is CE-5.1's territory and is already covered.
It must be: perform the guarded action in a repo with a broken link, and
observe the action refused.

- Break a link in a scratch clone, perform the action, assert non-zero and
  assert the message names the repo, the fragment, and the repair command.
- Repair it, repeat, assert the action succeeds. A check that refuses
  everything is not a check.

## Not obvious

- **Cost.** Whatever fires, time it in a healthy repo. If it is a pre-commit
  hook it runs on every commit forever; record the measured overhead rather
  than asserting it is small.
- **A repo with no `.claude/claude-md.json`.** Not every repo consumes
  fragments. The check must be silent there, not noisy and not a refusal.
- **claude-env itself.** Its link points inside its own repo. Confirm the check
  behaves the same there as in a consuming repo.
- **The escape hatch.** If the mechanism is bypassable, the message must say so
  plainly. A gate claiming to be unbypassable teaches people to hunt for the
  bypass and stop reading.

## Control

Disable the wiring, leave the link broken, repeat the action. It must succeed —
proving the wiring, not something incidental, is what refuses.
