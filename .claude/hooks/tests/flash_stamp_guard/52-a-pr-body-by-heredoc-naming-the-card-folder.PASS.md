# a pr body by heredoc naming the card folder -> PASS.
#
# gh reads its body from stdin; the text is data.
COMMAND=$'gh pr create --base develop --title t --body-file - <<\'EOF\'\nCopy it to out/flash/5-fullres/ when it\'s stamped.\nEOF'
