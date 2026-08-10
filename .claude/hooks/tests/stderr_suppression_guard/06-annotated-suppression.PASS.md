# The documented escape hatch. A suppression that says why it is there is a
# decision, not an accident, and the guard must honour its own instruction.
COMMAND="wsl.exe --status 2>/dev/null  # STDERR-SUPPRESS: probing whether interop is enabled"
