# No docs/decisions.md at all -> nothing to scan against, silent.
setup() {
  mkdir -p docs/implementation-plans/x
  cat > docs/implementation-plans/x/phase_04.md <<'PLAN'
- overview-single-screen.AC4.2 Success: emphasized box area > median non-emphasized box area.
PLAN
}
EXPECT="silent"
