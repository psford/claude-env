# No refspec: git pushes the current branch, which is main. -> BLOCK.
setup() { git branch -M main; }
COMMAND='git push'
