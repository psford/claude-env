# Runbook — two-party merge

**What this buys.** GitHub refuses to let an author approve their own pull
request. That refusal is server-side and not configurable, so requiring one
approving review means neither party can merge its own work. It is the cheapest
real separation of duties available here, and it needs nothing built.

**Why it was needed.** Checked 2026-08-09: every repo had
`required_approving_review_count: 0`. A pull request was required; a review was
not. The agent's token carries `Pull requests: write`, so it could open a PR and
merge it. "Only Patrick merges" was enforced by a local hook — and the CH-8
retrospective established what a hook is worth: the agent can edit it, and nine
of eleven spellings walked past the one guarding `main`.

## Audit

```
helpers/enforce-branch-protection.sh --verify
```

Reports `<protected>/admins=<bool>/pr=<yes|no>/rev=<count>` per repo. A repo is
only counted as enforced when `admins=true`, `pr=yes` **and** `rev>=1`. A review
count of zero is not enforcement; it is a requirement the author satisfies
alone, which is how this went unnoticed.

## Applying it

The agent cannot do this, by design — its token has `Administration: read`, and
a 403 on the write is the boundary working. Run from **Windows PowerShell**, not
inside WSL: `gh` inside WSL stores its token at `~/.config/gh/hosts.yml`, which
the agent can read, so authenticating there with admin credentials would hand it
the ability to undo this setting.

```powershell
gh api -X PATCH repos/psford/<repo>/branches/<branch>/protection/required_pull_request_reviews -F required_approving_review_count=1
```

`-F` and not `-f`: the field is an integer, and `-f` sends the string `"1"`.

Verify:

```powershell
gh api repos/psford/<repo>/branches/<branch>/protection/required_pull_request_reviews --jq .required_approving_review_count
```

Mind the branch — six repos use `master`, not `main`. The audit prints the
production branch per repo; do not assume.

## State

| | before | after | when |
|---|---|---|---|
| claude-harness | `admins=true pr=yes rev=0` | `rev=1` | 2026-08-09 |
| claude-env | `admins=true pr=yes rev=0` | `rev=1` | 2026-08-09 |

Outstanding at `rev=0`: `autoidlab_sql`, `bsky-feed-filter`, `claude-config`,
`claude-mac-env`, `gpu-crash-analyzer`, `imageResizer`, `imageResizerDropbox`,
`imageResizerGeneric`, **`photo-portfolio`**, **`road-trip`**,
`stock-analyzer`, `whisper-service`, `win-audio-analyzer`.

The two in bold are live production apps.

## Verified behaviour

Attempting to approve your own PR:

```
failed to create review: GraphQL: Review Can not approve your own pull request
mergeStateStatus: BLOCKED     reviewDecision: REVIEW_REQUIRED
```

That refusal comes from GitHub, not from a hook — which is the whole point.

`gh pr merge` was deliberately **not** attempted. Attempting the forbidden
action in order to test the guard against it would be the violation the guard
exists to prevent, and GitHub's own reported state is the honest evidence.

## The direction that could bite

With `enforce_admins: true` nobody bypasses this, so Patrick's own pull requests
need an approving review too. The agent holds `Pull requests: write` and can
supply one. If that ever stops working, the rule blocks all of his work and will
be switched off within a day — so it is an acceptance criterion (CH-30 AC3), not
an assumption.
