# CE-2.29. A filename whose hyphenated part has an r before an f -> PASS.
#
# The rm-rf pattern once accepted a hyphen in the MIDDLE of a word, so
# `-brief` read as a flag cluster: hyphen, b, r, ie, f. This exact command was
# refused on 2026-09-12, and so was the commit message that named the file.
# A flag starts at the start of a word; a filename's inner hyphen is not one.
setup() { git checkout -q -b feature/x; }
COMMAND='git rm -q plugins/psford-tickets/briefs/qa-adversarial-brief.md'
