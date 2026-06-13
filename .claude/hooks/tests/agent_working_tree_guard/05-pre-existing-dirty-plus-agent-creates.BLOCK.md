# Tree was dirty before the agent ran, agent ALSO creates a new file.
# Guard MUST report the new file but NOT the pre-existing dirty one
# (delta-only semantics — only what the agent caused).
BASELINE_FILES=(README.md notes.txt)

pre_dirty() {
  printf 'edited by user\n' > notes.txt
}

agent_mutations() {
  printf 'wandered\n' > agent-output.txt
}

EXPECT=agent-output.txt
EXPECT_NOT=notes.txt
