# Remote named but no refspec still pushes the current branch. -> BLOCK.
setup() { git branch -M main; }
COMMAND='git push origin'
