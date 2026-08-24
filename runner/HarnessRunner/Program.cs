using HarnessRunner;

// The Windows build runner. It exists because WSL cannot build a net8.0-windows
// project -- `dotnet build` there dies with MSB4019, the WindowsDesktop SDK is
// not on Linux, and one Windows-only project takes the whole solution with it.
//
// It is STARTED BY PATRICK and does not run otherwise. Installed as a Windows
// service with StartupType=Manual, it is off at boot and comes up on
// Start-Service. That is the control, deliberately: the trust boundary is
// already crossed whenever he runs code this project wrote, so what a daemon
// changes is not whether arbitrary code can reach Windows but how often a human
// decides it may. Anything that makes this start on its own -- Automatic
// startup, a Run key, a Startup shortcut, a scheduled task -- removes the only
// control the design has, and a test fails the build if one appears.
//
// The routes live in RunnerApp so the tests exercise them rather than a copy.

var port = int.TryParse(Environment.GetEnvironmentVariable("HARNESS_RUNNER_PORT"), out var p)
    ? p : RunnerApp.DefaultPort;

// The allowlist lives in the /mnt/c carve-out, not beside this service, so WSL
// can WRITE it and Windows can READ it -- which is what makes registering a repo
// a file write from the Linux side instead of a mutation endpoint here. An
// endpoint that edited the allowlist would be a way to widen the allowlist over
// HTTP, which is the one thing the allowlist exists to prevent.
var allowlistPath = Environment.GetEnvironmentVariable("HARNESS_RUNNER_PROJECTS")
    ?? @"C:\Users\patri\Documents\claudeProjects\projects\harness-runner-projects.json";

RunnerApp.Build(allowlistPath, port).Run();

public partial class Program { }
