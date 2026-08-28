# Copying a tree is not a mutation harness on its own. -> PASS.
TOOL_NAME="Write"
FILE_PATH="tools/backup.py"
CONTENT='import shutil
shutil.copytree("/home/patrick/projects/x", "/backup/x")'
