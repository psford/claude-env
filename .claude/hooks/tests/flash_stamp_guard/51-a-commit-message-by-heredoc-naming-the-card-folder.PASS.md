# a commit message by heredoc naming the card folder -> PASS.
#
# A heredoc's body is data for the command it feeds. git only reads it, so a message that
# names out/flash paths, with an apostrophe in it, is no write anywhere. Wrongly blocked
# before: the body was read as commands, and the apostrophe made the whole command unreadable.
COMMAND=$'git commit -q -F - <<\'EOF\'\nfeat: stage the probe\n\nThe probe\'s build goes to out/flash/2-sensor-3/DITHERWARE.BIN.\nEOF'
