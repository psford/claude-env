# Tree was DIRTY before the agent ran (snapshot captures it), agent does
# NOTHING. Delta is empty → guard MUST stay silent. This is the regression
# class Patrick caught me on 2026-06-11: "false positive, continuing." With
# delta-only design, there IS no false positive — pre-existing dirty is
# subtracted out.
BASELINE_FILES=(README.md notes.txt)

pre_dirty() {
  printf 'edited by user before agent ran\n' > notes.txt
}

EXPECT=silent
