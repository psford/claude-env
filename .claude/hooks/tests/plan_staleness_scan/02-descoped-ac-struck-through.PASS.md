# The plan file already strikes the descoped AC -> annotated, silent.
setup() {
  mkdir -p docs/implementation-plans/x
  cat > docs/decisions.md <<'DEC'
## emphasize sizing
2026-06-26: overview-single-screen.AC4.2 DESCOPED — incompatible with the fill.
DEC
  cat > docs/implementation-plans/x/phase_04.md <<'PLAN'
- ~~overview-single-screen.AC4.2 Success: emphasized box area > median non-emphasized box area.~~
PLAN
}
EXPECT="silent"
