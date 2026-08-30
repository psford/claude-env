# CE-2.8 — ci_cost_guard decides on reachable triggers

Run: `bash .claude/hooks/tests/run-hook-tests.sh ci_cost_guard`. The fixture
suite already covers the block/pass shapes, so this adds cases rather than a
harness.

## What must not weaken

This guard exists because three iOS builds in seven minutes cost three weeks of
GitHub CI. Write these first and make sure each still blocks.

- `gh workflow run` on a repo with a macOS job: **permanently** blocked, no
  bypass, unchanged. This is the path the July incident came through and it is
  not what this ticket touches.
- A push to a repo whose macOS job IS reachable from a push: still blocked.
- A repo with ordinary ubuntu workflows and no ack: still blocked on dispatch.

If any of those go green, stop — the fix went too far.

## The case being added

A macOS job in a workflow whose triggers are `workflow_dispatch` only cannot
fire on push, so the push must not be blocked. Build both halves in one fixture
pair so the difference is the trigger and nothing else:

    ios-ci.yml   runs-on: macos-15   on: [workflow_dispatch]   -> push PASSES
    ios-ci.yml   runs-on: macos-15   on: [push]                -> push BLOCKS

Same file, same runner, one line different. A fixture that also changed the
runner would pass for the wrong reason.

## Not obvious, and where this will actually go wrong

- **`on` parses as the boolean True.** YAML 1.1 reads a bare `on:` key as
  `True`, not `"on"` — `yaml.safe_load(...)["on"]` raises KeyError on a file
  that is perfectly valid. Seen while diagnosing this ticket. Cover a workflow
  written both ways (`on:` and `"on":`) and assert the same verdict.
- **Trigger forms vary.** `on: push`, `on: [push]`, and `on:\n  push:\n
  branches: [main]` are all push-triggered and all parse to different shapes
  (str, list, dict). One fixture each.
- **A malformed workflow must BLOCK.** Seed a file that is not valid YAML and
  assert the push is refused. An exception swallowed into "no push trigger
  found, therefore safe" is how this becomes a bypass — the same failure mode as
  a missing linter exiting 0.
- **A repo with no `.github/workflows` at all** stays silent, as today.
- **Mixed repo**: one dispatch-only macOS workflow AND one push-triggered ubuntu
  workflow — road-trip exactly. Must pass. The ubuntu run is a cost Patrick has
  said is fine; the point is not to block it on macOS grounds.
- **A macOS job in a push-triggered workflow that also has a `paths:` filter**
  is out of scope: knowing whether the filter matches needs the diff. It must
  BLOCK, and the plan says so rather than leaving the reader to wonder — erring
  toward refusal is the standing policy.

## The message

Assert on it, not only the exit code. The refusal must name the offending
workflow file and say to make it dispatch-only or drop the macOS job. It must
NOT offer an ack — the escape hatch it used to print was unreachable, and
replacing one unusable bypass with a usable one is not this ticket.

A control: replace the whole message with a bare `return 2`. Every behavioural
test should still pass and only the message tests fail. If a behavioural test
fails too, it was asserting on message text by accident.

## The third defect, found while writing this plan

`DISPATCH_RE` matches `gh workflow run` anywhere in the raw command, including
inside a quoted string. `ticket ac add CE-2.8 --text "...gh workflow run..."`
was refused as an attempt to trigger CI.

Fixture: a command whose only occurrence of the phrase is inside a quoted
argument must not be blocked. Fixing it properly means asking whether the phrase
is the command being run rather than data being passed to one — the same
question CH-192.2 is about. If that turns out to be more than a small change,
split it out and say so rather than half-doing it here.

## Control for the whole ticket

Revert the trigger parsing so the guard decides on the substring again. The new
dispatch-only fixture must fail and every must-not-weaken fixture must still
pass. That separates "the new logic allows this" from "something else was
allowing it".
