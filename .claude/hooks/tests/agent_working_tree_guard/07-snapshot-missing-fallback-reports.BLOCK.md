# No pre-snapshot was written (simulates Pre hook didn't fire). Tree is
# dirty post-call. Guard MUST fall back to "report everything dirty"
# (safer default for missing baseline) and include the fallback note.
BASELINE_FILES=(README.md)
SKIP_SNAPSHOT=1

agent_mutations() {
  printf 'wandered\n' > orphan.txt
}

EXPECT=orphan.txt
