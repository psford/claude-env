# Commit modifies only impl (no tests). Not a test-only commit, so the
# RED convention does not apply. Hook MUST pass silently.

setup_repo() {
  mkdir -p src
  echo "baseline" > README.md
  git add README.md
  git commit -q -m "baseline"

  echo "new feature impl" > src/feature.ts
  git add src/feature.ts
  git commit -q -m "feat(feature): add new feature impl"
}
