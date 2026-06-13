# Clean tree, agent creates a new file → guard MUST fire and report it.
BASELINE_FILES=(README.md)

agent_mutations() {
  printf 'sneaky\n' > wandered.txt
}

EXPECT=wandered.txt
