# A dispatch in a repo that has no workflows at all -> PASS.
#
# CH-237.9, AC4. The tightening in 21-24 widened what the guard LOOKS at, and
# the failure mode of that kind of change is a blanket refusal: every push and
# every dispatch blocked everywhere, which costs exactly as much trust as the
# false positives CE-2.8 was filed for.
#
# 07 pins the push half of this. Nothing pinned the dispatch half, so a
# regression here would have been silent.
setup() {
  :
}
COMMAND="gh workflow run ci.yml"
