# Matched on BEHAVIOUR, not vocabulary: renaming the file changes nothing. -> BLOCK.
TOOL_NAME="Write"
FILE_PATH="tools/helpful_checker.py"
CONTENT='shutil.copytree(src, dst)
subprocess.run(["pytest", dst])'
