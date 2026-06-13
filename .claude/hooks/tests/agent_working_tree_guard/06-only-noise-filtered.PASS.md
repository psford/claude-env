# Agent only touches noise-prefix paths (test-results/) → guard MUST stay
# silent. Noise filter applies post-delta so this is a green case.
BASELINE_FILES=(README.md)

agent_mutations() {
  mkdir -p test-results
  printf 'junit xml\n' > test-results/output.xml
}

EXPECT=silent
