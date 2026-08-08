# A src:dst refspec landing somewhere other than trunk. -> PASS.
setup() { git checkout -q -b feature/x; }
COMMAND='git push origin develop:develop'
