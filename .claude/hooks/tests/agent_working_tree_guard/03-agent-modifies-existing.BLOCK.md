# Clean tree, agent modifies a baseline file → guard MUST fire and report it.
BASELINE_FILES=(src/app.ts)

agent_mutations() {
  printf 'mutated by agent\n' > src/app.ts
}

EXPECT=src/app.ts
