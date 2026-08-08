# A commit message documenting the rule blocked its own commit on 2026-08-07. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND="git commit -q -F - <<'EOF'
fix(hooks): document the rule

The guard matched forced pushes naming main, e.g. git push --force origin main,
but not a plain refspec push.
EOF"
