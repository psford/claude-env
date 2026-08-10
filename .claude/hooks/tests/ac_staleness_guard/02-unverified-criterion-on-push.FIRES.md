# The case it exists for, and only reachable since CH-58: the status file now
# comes from the repo being pushed, so a fixture can supply one. Before, it read
# claude-env's copy no matter which repo you pushed from.
setup() {
  mkdir -p infrastructure/wsl
  cat > infrastructure/wsl/ac-status.json <<'INNER'
{"criteria": {"AC1": {"status": "unverified", "description": "the sandbox boundary holds"}}}
INNER
  git add -A && git commit -qm "chore: ac status"
}
COMMAND='git push origin feature/x'
EXPECT_MATCH='AC1|unverified'
