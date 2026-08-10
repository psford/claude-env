# Same shape: writing a fixture that mentions a dotnet+Azure command made it fire.
COMMAND='cat > fixture.md <<EOF
COMMAND=WSL_SQL_CONNECTION="Server=tcp:x.database.windows.net;" dotnet run
EOF'
