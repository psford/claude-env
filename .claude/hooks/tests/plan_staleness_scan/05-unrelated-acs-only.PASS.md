# Plan references only ACs that are NOT descoped -> silent.
setup() {
  mkdir -p docs/implementation-plans/x
  cat > docs/decisions.md <<'DEC'
## emphasize sizing
2026-06-26: overview-single-screen.AC4.2 DESCOPED — incompatible with the fill.
DEC
  cat > docs/implementation-plans/x/phase_04.md <<'PLAN'
- overview-single-screen.AC1.1 Success: overview loads within budget.
PLAN
}
EXPECT="silent"
