# Stack: .NET Windows Service

<!-- Canonical source: claude-env/shared/claude-md/stack-windows-service.md. -->
<!-- Shared by SysTTS, whisper-service, and any future .NET Windows-service repo. -->

## Build & Run
- `dotnet build`, `dotnet test`, `dotnet run`. Windows-only scripts run via PowerShell (`powershell.exe -Command "..."` from WSL).
- Configuration changes (`appsettings.json`) require an application restart — there is no hot reload for a tray/service host.
- Treat compiler warnings as errors before committing.

## Testing
- Stack: **xUnit + Moq + FluentAssertions**.
- Test naming: `MethodName_Condition_Expected`.
- Structure every test Arrange / Act / Assert.
- `dotnet test` must pass before committing (run all, or filter by class during dev).

## Coding Conventions
- C# (.NET 8): PascalCase types/methods, camelCase locals/fields.
- Nullable enabled: use `??` for defaults; avoid `!` (null-forgiving) unless justified.
- Prefer `async`/`await`; offload long-running synthesis/IO with `Task.Run`.
- Logging via `ILogger` from DI; no `Console.WriteLine` in production paths.

## Service / Host Patterns
- Tray + Kestrel hosts: marshal UI/STA-thread work off background request threads via the captured `SynchronizationContext`.
- Long native callbacks (e.g. Win32 hooks) must offload work to stay within their callback deadline.

## CI / Release
- CI is the shared reusable workflow: `psford/claude-env/.github/workflows/windows-service-build-release.yml@main`. The companion repo's workflow is a thin wrapper passing `app_name`, `project_path`, `appsettings_source`.
- Releases are self-contained executables + a Windows Service install script, published as GitHub Releases (zip + SHA256).
- Deployment to a Windows host uses `infrastructure/windows-deploy/deploy-app.ps1` against the app registry.
