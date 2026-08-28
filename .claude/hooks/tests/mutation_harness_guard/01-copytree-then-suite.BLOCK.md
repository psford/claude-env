# The exact shape of the four scratch harnesses written on 2026-08-28. -> BLOCK.
TOOL_NAME="Write"
FILE_PATH="scratch/verify_pin.py"
CONTENT='import shutil, subprocess, sys
shutil.copytree(REPO, copy)
subprocess.run([sys.executable, "plugins/psford-tickets/tests/test_ticket.py"])'
