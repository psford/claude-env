# The exact shape of the four scratch harnesses of 2026-08-28: copy, edit, run.
# -> BLOCK.
TOOL_NAME="Write"
FILE_PATH="scratch/verify_pin.py"
CONTENT='import shutil, subprocess, sys
shutil.copytree(REPO, copy)
target.write_text(src.replace(search, replace, 1))
subprocess.run([sys.executable, "plugins/psford-tickets/tests/test_ticket.py"])'
