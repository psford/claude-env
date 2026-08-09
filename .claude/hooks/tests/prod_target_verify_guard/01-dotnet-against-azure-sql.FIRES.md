# dotnet plus a connection string pointing at Azure SQL: the case it exists for.
COMMAND='WSL_SQL_CONNECTION="Server=tcp:roadtripmap-db.database.windows.net;" dotnet run'
EXPECT_MATCH='WSL_SQL_CONNECTION'
