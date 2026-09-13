# A heredoc written to a file, followed by a statement that does not name
# it -> SILENT.
#
# CE-13.7 made a body code whenever ANYTHING followed the terminator, which
# is true of the dangerous case and of almost every harmless one. `echo
# done` cannot run notes.md, and reading that body turned prose about a
# dispatch into a dispatch -- the defect CE-2.20 and CE-2.26 exist to
# remove, reintroduced by a fix for a different one.
#
# THIS REPO'S SUITE DID NOT CATCH IT. claude-harness carries a byte-identical
# copy of the parser, and its guard tests went red the moment the copy was
# brought into step. All 309 fixtures here passed on the defect. This fixture
# is why that cannot happen again from this side.
#
# RED at 705e24e, where the body was read and the dispatch text inside it
# fired the guard.
COMMAND=$'cat > notes.md <<DESC\nwe banned gh workflow run ios.yml in 2026\nDESC\necho done'
