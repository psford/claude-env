# cd elsewhere then cp elsewhere -> PASS.
#
# Following cd mustn't make the gate reach commands that never touch a card folder.
COMMAND='cd /tmp && cp a.txt b.txt'
