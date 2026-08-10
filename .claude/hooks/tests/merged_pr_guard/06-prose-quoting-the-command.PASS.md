# A document that quotes `gh pr edit` is not running it. This guard refused its
# own verification script on 2026-08-09 for exactly this reason.
COMMAND='cat > notes.md <<EOF
Do not run: gh pr edit 7 --title "x" on a merged PR.
EOF'
GH_STATE="MERGED"
