# Phase file references the DESCOPED AC unannotated, but carries an AC-DESCOPE-OK bypass -> PASS.
setup() {
  mkdir -p docs/implementation-plans/x
  cat > docs/implementation-plans/x/test-requirements.md <<'DOC'
| AC | Description | Phase | Notes | Browsers |
|----|-------------|-------|-------|----------|
| **AC4.2** | ~~emphasized box area > median non-emphasized~~ | — | **DESCOPED v1** — emphasis sizing dropped. | — |
DOC
  cat > docs/implementation-plans/x/phase_01.md <<'DOC'
<!-- AC-DESCOPE-OK: historical reference only, kept for context -->
- **AC4.2 Success:** emphasized box area > median non-emphasized box area.
DOC
  git add docs/implementation-plans/x/
}
