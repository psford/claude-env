# Phase file already notes DESCOPED on the same line as the AC reference -> PASS.
setup() {
  mkdir -p docs/implementation-plans/x
  cat > docs/implementation-plans/x/test-requirements.md <<'DOC'
| AC | Description | Phase | Notes | Browsers |
|----|-------------|-------|-------|----------|
| **AC4.2** | ~~emphasized box area > median non-emphasized~~ | — | **DESCOPED v1** — emphasis sizing dropped. | — |
DOC
  cat > docs/implementation-plans/x/phase_01.md <<'DOC'
- AC4.2 (DESCOPED — see decisions.md, no longer a hard requirement).
DOC
  git add docs/implementation-plans/x/
}
