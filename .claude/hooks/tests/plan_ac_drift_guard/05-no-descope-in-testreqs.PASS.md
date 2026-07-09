# test-requirements.md marks nothing DESCOPED -> nothing to drift-check, PASS.
setup() {
  mkdir -p docs/implementation-plans/x
  cat > docs/implementation-plans/x/test-requirements.md <<'DOC'
| AC | Description | Phase | Notes | Browsers |
|----|-------------|-------|-------|----------|
| **AC1.1** | overview loads within budget | 1 | — | — |
DOC
  cat > docs/implementation-plans/x/phase_01.md <<'DOC'
- **AC1.1 Success:** overview loads within budget.
DOC
  git add docs/implementation-plans/x/
}
