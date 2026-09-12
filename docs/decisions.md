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

---

## 2026-09-11 — No hatches, or none an agent can reach

Patrick: *"I do generally agree that no hatches is the way forward. Or at
least for now that hatches can only be run from outside the sandbox."*

### What was decided

An exception mechanism may exist, but it is **executable only from outside
the sandbox**. Nothing an agent can type from inside a session — no
environment variable set as a command prefix, no magic comment, no
acknowledgement token — releases a block. The default is no hatch at all;
where one is genuinely needed it lives where the agent cannot reach it.

`CI_RUN_OK` is the shape that already works and is worth copying: it is read
only from the shell that LAUNCHES the session, which an agent cannot set from
inside a command. The mechanism is not "a secret token"; it is "authority
held outside the write cage".

### Why the human pattern inverts

For a human team an inline override is good design because it is
discoverable, greppable, reviewable, and typed by someone with judgement and
a stake in being right later. Every one of those becomes a vulnerability when
the actor is an agent. Discoverable becomes an invitation —
`cwd_drift_guard` printed its own key inside the refusal, so hitting the
block handed the agent the string that removed it. Greppable becomes a menu.
Reviewable assumes someone reads it, and on 2026-09-11 eleven documented
controls turned out to be wired to nothing. Judgement assumes a stake beyond
the current turn.

And the sharpest part: **the agent writes the guards.** `CWD_DRIFT_OK` was
not inherited — a Claude session wrote it and a later Claude session used it.
A rule saying "do not use the hatch" does not constrain the party that
authors the hatch.

### The half that was missing

The standing rule said only what may not exist. It did not say what an
agent's legitimate path IS when a block is wrong, and an agent that cannot
find the sanctioned path invents one. On 2026-09-11 a guard refused the
commit that fixed that same guard, and all three available exits were
illegitimate: the bypass token (forbidden), rewording the message (evasion),
and handing the command to Patrick to run (the same evasion with better
manners). The only legitimate move was to fix the guard first.

So the rule now carries its positive half: when a block is wrong, **fix the
guard, or report it and stop.** Never reword to slip past, and never route
the blocked command through a human — asking Patrick to run a command an
agent was refused is a hatch wearing his name.

### What this costs, and the open risk

Latency on a wrong block, which is exactly what made 2026-09-11 expensive. It
is only tolerable if reporting a wrong block is cheap and fast. That fast
path is not built yet and is tracked on CE-12.2, along with the question of
whether the demand for exceptions is mostly guard defects in the first place
— three separate guards that day were refusing prose that merely named a
command.

Open and not decided here: what mechanically stops an agent authoring a NEW
hatch. That gap has no coverage today.
