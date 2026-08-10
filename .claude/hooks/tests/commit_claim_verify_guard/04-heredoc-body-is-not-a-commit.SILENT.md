# A heredoc BODY that quotes a commit is data, not a command.
# Observed live on 2026-08-09: writing this very fixture file made the guard fire,
# because the heredoc text contained `git commit -m "... verified ..."`.
COMMAND='cat > fixture.md <<EOF
COMMAND=git commit -m "fix: verified against the live endpoint"
EOF'
