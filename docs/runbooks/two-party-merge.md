# Runbook — two-party merge

**What this buys.** Neither party can merge its own work. GitHub refuses to let
an author approve their own pull request, that refusal is server-side and not
configurable, and — crucially — the agent and the human are now *different
GitHub accounts*, so the rule bites where it is meant to.

**Status: not currently in force.** `required_approving_review_count` is `0` on
both repos. Verified indirectly on 2026-08-09: PRs #22 and #23 merged with no
reviews recorded. See *Turning it on* below.

---

## The first attempt, and why it failed

The original design was just "require one approving review". That is correct in
general and useless here, because **the agent's token was Patrick's account**.
GitHub saw one identity, so the self-approval refusal blocked *him* too, and
every pull request became permanently unmergeable. It was reverted within the
hour.

The mistake worth remembering: the mechanism was verified (GitHub really does
refuse self-approval) while the premise was not (that there were two parties).

## The mechanism that works

Two GitHub accounts:

| | account | repo role | credential lives |
|---|---|---|---|
| human | `psford` | Admin | **not on this machine** |
| agent | `PatricksRobot` | Write | `~/.config/gh/hosts.yml` in WSL |

`PatricksRobot` holds a **classic PAT with `repo` and `read:org` only**. Its
ceiling is the *collaborator role*, not the token scopes: Write, not Admin, so
it cannot change branch protection, alter repo settings, or bypass protection
rules regardless of what the token says.

Git transport matters as much as the API. The remotes were moved from SSH to
HTTPS, because SSH was still authenticating with Patrick's key — leaving the API
as the robot and the transport as him is the kind of half-boundary that looks
solid and is not.

### Verified, all four directions

| case | result |
|---|---|
| a PR the agent opens is authored by `PatricksRobot` | ✓ |
| the agent cannot approve its own PR | ✓ `Can not approve your own pull request` |
| Patrick can approve what the agent opens | ✓ `psford: APPROVED` on #18 |
| the agent can approve what Patrick opens | ✓ `PatricksRobot: APPROVED` on #20 |

The fourth matters most operationally: without it, turning the requirement on
blocks all of Patrick's own work, and the rule gets switched off within a day.

The boundary was also checked from the inside — the agent attempting to set the
review count back to `0` returns `403 Resource not accessible by personal access
token`.

## Turning it on

The agent cannot do this, by design. Run from **Windows PowerShell**, not inside
WSL: `gh` in WSL stores its token where the agent can read it, so authenticating
there with admin credentials would hand it the ability to undo this.

```powershell
gh api -X PATCH repos/psford/claude-harness/branches/main/protection/required_pull_request_reviews -F required_approving_review_count=1
gh api -X PATCH repos/psford/claude-env/branches/main/protection/required_pull_request_reviews -F required_approving_review_count=1
```

`-F`, not `-f`: the field is an integer and `-f` sends the string `"1"`.

Verify:

```powershell
gh api repos/psford/claude-harness/branches/main/protection/required_pull_request_reviews --jq .required_approving_review_count
```

### `main` only

Not `develop`. Trivial changes go directly onto develop by design, and a pull
request requirement there would forbid exactly the small commits it exists to
allow.

### Not the other repositories

The other repos have no `PatricksRobot` collaborator, so the same setting would
deadlock them exactly as it deadlocked these two. Add the collaborator first, or
leave them.

## Auditing

```
helpers/enforce-branch-protection.sh --verify
```

Reports `<protected>/admins=<bool>/pr=<yes|no>/rev=<count>` per repo, and counts
a repo as enforced only when `rev>=1` — a review requirement of zero is one the
author satisfies alone, which is how this went unnoticed for months.

**Patrick must run it.** The agent's token has no `Administration` scope, so
branch protection is unreadable from this machine. That is the boundary working,
and it means the audit is his.

## Approving, in the UI

The Approve control is on the **Files changed** tab, not Conversation: green
**Submit review** button → select **Approve** → **Submit review** again in the
panel. The `Request` link beside a name in the Reviewers sidebar requests a
review; it does not give one.
