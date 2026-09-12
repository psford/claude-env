# A definition in a heredoc body fed to a shell -> BLOCK.
#
# strip_heredoc_bodies keeps an interpreter's body inline precisely
# because the body is code. The definition then lands on its own line,
# which is what makes the newline separator load-bearing.
#
# CE-2.19, QA round 1.
TOOL_NAME="Bash"
COMMAND='bash <<'\''EOF'\''
cd() { :; }
EOF'
