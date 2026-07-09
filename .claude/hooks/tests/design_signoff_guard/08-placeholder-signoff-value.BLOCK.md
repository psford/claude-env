# Sign-off line exists but with a placeholder value (unbolded "Sign-off: TBD") -> still BLOCK.
# Note: SIGNOFF_RE's `\*{0,2}` closing-asterisk match sits BEFORE the colon, so a
# "**Sign-off:** TBD" (closing ** placed after the colon, the common bold-label
# convention) sweeps "**" into the captured value and evades PLACEHOLDER_VALUE_RE.
# Real design docs in this repo never carry a pre-signoff "Sign-off:" placeholder
# line at all (they just omit it, see fixture 01/02) so this fixture uses the
# unbolded form the regex was written to catch.
setup() {
  mkdir -p docs/design-plans
  cat > docs/design-plans/2026-06-26-overview-single-screen.md <<'DOC'
# Overview single-screen design

Sign-off: TBD
DOC
  git add docs/design-plans/2026-06-26-overview-single-screen.md
  git commit -q -m "unsigned design doc"

  mkdir -p src/pages
  printf '<div>hi</div>\n' > src/pages/index.astro
  git add src/pages/index.astro
}
