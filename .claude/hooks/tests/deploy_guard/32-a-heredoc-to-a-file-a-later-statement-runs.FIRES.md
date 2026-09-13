# A heredoc written to a file that a LATER statement names -> FIRES.
#
# The other half of fixture 31, and the rig CE-13.7 closed: the body lands on
# disk and the next statement runs it. No interpreter is named anywhere in
# the rule -- the question is whether anything after the terminator
# REFERENCES the file the feeder wrote, which is finite because the
# destination is on the feeder line.
#
# Keeping both fixtures is the point. 31 alone would pass against a guard
# that had simply stopped reading heredoc bodies altogether, which is the
# hole the CSO gate reproduced twice on 2026-09-12.
COMMAND=$'cat > /tmp/r.sh <<EOF\ngh workflow run ios.yml\nEOF\nbash /tmp/r.sh'
EXPECT_MATCH="not permitted to trigger GitHub workflow runs"
