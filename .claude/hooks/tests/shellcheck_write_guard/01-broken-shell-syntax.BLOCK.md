# Writing a .sh that `bash -n` rejects.
TOOL_NAME="Write"
FILE_PATH="bad.sh"
CONTENT='if [ 1 -eq 1 ]
then echo hi
'
