# `git merge-base` INSPECTS two branches; it writes nothing. -> PASS.
#
# CE-2.1, 2026-08-27. The reverse-merge matcher is `\bmerge\b.*\bmain\b`, and
# `\b` fires inside `merge-base` because `-` is not a word character. So asking
# where develop and main diverged was refused as "Merging main INTO develop",
# with a refusal naming no way forward -- while diagnosing that very divergence.
#
# The existing read-only fixtures (20, 21) all run on `feature/x`, and this
# matcher only arms on `develop`, so none of them could reach it.
#
# Class, not instance: `merge-tree` and `merge-file` are the same shape. The fix
# is a `(?!-)` lookahead, so `git merge main` still blocks and `merge-anything`
# does not. `--merges` and `--merged` were always safe -- no word boundary
# before the trailing letter.
setup() { git checkout -q -b develop; }
COMMAND='git merge-base develop origin/main'
