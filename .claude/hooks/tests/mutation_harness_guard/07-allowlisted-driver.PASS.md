# The committed, reviewed driver stays editable -- it is the sanctioned tool. -> PASS.
TOOL_NAME="Write"
FILE_PATH="plugins/psford-tickets/tests/mutation_smoke.py"
CONTENT='shutil.copytree(REPO, repo_copy)
subprocess.run([sys.executable, "plugins/psford-tickets/tests/test_ticket.py"])'
