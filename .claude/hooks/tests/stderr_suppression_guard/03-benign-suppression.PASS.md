# Suppressing stderr on a harmless command is not the sin. Blocking every
# 2>/dev/null would make this guard the first one switched off.
COMMAND='ls /tmp 2>/dev/null'
