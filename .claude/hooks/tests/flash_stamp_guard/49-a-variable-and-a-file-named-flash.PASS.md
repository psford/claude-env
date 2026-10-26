# a variable and a file named flash -> PASS.
#
# A wrong block found live on 2026-10-26: a test loop ($t) that named flash_stamp_guard.py
# was refused as "a path built when the shell runs", because "flash" was matched anywhere in
# the text. Only a path through a folder named flash concerns the gate.
COMMAND='for t in a b; do python3 .claude/hooks/tests/$t.py; done; ls flash_stamp_guard.py settings.before-flash-gate.json'
