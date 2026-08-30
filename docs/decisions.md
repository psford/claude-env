# Decisions

Design decisions for claude-env, newest first. CLAUDE.md's PRODUCT DECISIONS
rule says a decision Patrick makes gets recorded here; a decision an agent
makes on his behalf belongs here too, with the reasoning that would let him
overturn it.

## 2026-08-30 — git-flow-develop-main stops being parameterised; git-flow-trunk stays (CE-5.6)

Under CE-5, a shared fragment carrying no `{{VARS}}` is symlinked into each
repo instead of copied, so it exists in one file and cannot drift. Fragments
that carry variables must still be generated, because a symlink cannot turn
`{{WORKING_BRANCH}}` into `develop`.

That left `git-flow-develop-main` and `git-flow-trunk` as the only two
fragments still copied into every repo that uses them, and the only reason the
generation path exists at all. The question was whether to enumerate them —
one invariant fragment per branch layout — so that every fragment links and
substitution could be deleted.

### The check that decided it

The proposal assumed the two fragments differ only in branch names. They do
not. With every branch token normalised to the same string, **57 of 62 lines
still differ.**

They describe different workflows, not one workflow with two spellings.
`git-flow-develop-main` has a `develop → main` flow and a REVERSE MERGE
prohibition that only makes sense when two long-lived branches exist.
`git-flow-trunk` has "nothing reaches trunk except via PR", names server-side
branch protection with `enforce_admins`, and covers `git push origin
<branch>:trunk` as a CLI merge however it is spelled. Neither table is a
rewording of the other.

So enumeration was never available: these were not one fragment wearing two
values, and merging them to split them again would have invented the
duplication it was meant to remove.

### What the values actually are

Asked of every `.claude/claude-md.json` rather than assumed:

| Fragment | Repos | Distinct value sets |
|---|---|---|
| `git-flow-develop-main` | 8 | **1** — `develop` / `main`, every time |
| `git-flow-trunk` | 2 | **2** — `master` (T-Tracker), `main` (photo-portfolio) |

That is the real finding, and it splits the answer.

`git-flow-develop-main`'s parameter has never varied. Eight repos, one value.
It is a variable in name only, and it is the sole reason those eight repos
still hold a copy of their git-flow rules — which is where the commit, merge
and branch prohibitions live, so it is the worst fragment to have eleven copies
of.

`git-flow-trunk`'s parameter genuinely varies, over two values, and the fragment
is 41 lines of prose that would have to be duplicated to enumerate it.

### Decision

**De-parameterise `git-flow-develop-main`**: literal `develop` and `main`. It
becomes linkable, and the eight repos that use it inherit their git-flow rules
instead of copying them. Those repos then hold no fragment prose at all —
`CLAUDE.md` is the generated header plus `CLAUDE.local.md`.

**Keep `git-flow-trunk` parameterised.** Two values over 41 lines is exactly
the case a parameter is for. Splitting it into `git-flow-trunk-main` and
`git-flow-trunk-master` would create two near-identical files that can disagree
— a new home for drift, in the change made to end drift. That is the argument
against enumeration and it applies here even though it did not apply above.

**The substitution path stays.** Two repos need it, so it is not dormant code
and the exit-2 guard on an unsubstituted token still does real work.

### What this costs

A repo that ever wants a different two-branch layout — `develop → master`, say
— now needs a new fragment rather than a new value. That is the trade, and it
is acceptable at eight-of-eight agreement: the layout is a standard here, not a
per-repo preference. If a second layout ever appears, this decision should be
revisited rather than worked around by re-adding the variable, because a
variable with two values is a different thing from a variable with one.
