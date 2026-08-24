using System.Diagnostics;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Hosting;

namespace HarnessRunner;

/// <summary>
/// The whole service, built in one place so the tests exercise the REAL
/// endpoints rather than a copy of them.
///
/// The first draft of the test suite rebuilt the routes itself, which would have
/// tested a fossil: the copy could stay green while the shipped endpoints
/// changed underneath it. Everything a test wants to vary -- the port, the
/// allowlist path -- is a parameter here instead.
/// </summary>
public static class RunnerApp
{
    public const int DefaultPort = 8919;

    public static WebApplication Build(string allowlistPath, int port, string bindHost = "127.0.0.1")
    {
        var builder = WebApplication.CreateBuilder();
        // Loopback ONLY. Under WSL's mirrored networking 127.0.0.1 already
        // crosses between Windows and Linux, so binding wider buys nothing and
        // would put a build endpoint on the network.
        builder.WebHost.UseUrls($"http://{bindHost}:{port}");

        var allowlist = Allowlist.Load(allowlistPath);
        var app = builder.Build();

        app.MapGet("/health", () => Results.Ok(new
        {
            status = "ok",
            // So a caller can tell a RUNNING runner from a missing one, and
            // separately whether this box can build what it was asked for.
            // Without it, 200 OK only proves something is listening.
            sdks = InstalledSdks(),
            projects = allowlist.Keys,
            allowlist = allowlistPath,
        }));

        app.MapPost("/build", (RunRequest req) => Dispatch("build", req, allowlist));
        app.MapPost("/test", (RunRequest req) => Dispatch("test", req, allowlist));
        return app;
    }

    private static IResult Dispatch(string verb, RunRequest req, Allowlist allowlist)
    {
        var project = allowlist.Find(req.Project);
        if (project is null)
        {
            return Results.BadRequest(new
            {
                error = $"'{req.Project}' is not a registered project.",
                projects = allowlist.Keys,
                fix = "add an entry to the allowlist file, then restart the runner",
            });
        }

        var result = Builder.Run(verb, project);
        // 200 even when the build FAILS, carrying the real exit code. An HTTP
        // error status would be indistinguishable from the runner being down,
        // and telling those apart is the whole job of the wrapper on the other
        // side of this.
        return Results.Ok(new
        {
            exit_code = result.ExitCode,
            stdout = result.Stdout,
            stderr = result.Stderr,
            invocation = result.Invocation,
        });
    }

    public static string[] InstalledSdks()
    {
        try
        {
            var psi = new ProcessStartInfo("dotnet", "--list-sdks")
            {
                UseShellExecute = false,
                RedirectStandardOutput = true,
            };
            using var p = Process.Start(psi);
            if (p is null) return Array.Empty<string>();
            var text = p.StandardOutput.ReadToEnd();
            p.WaitForExit();
            return text.Split('\n', StringSplitOptions.RemoveEmptyEntries)
                       .Select(l => l.Trim()).Where(l => l.Length > 0).ToArray();
        }
        catch
        {
            return Array.Empty<string>();
        }
    }
}

/// <summary>
/// The entire request surface: a project KEY. No command, no arguments, no path,
/// no shell string. A new field here is a new way to influence what runs, so a
/// test fails the build if one appears with a name of that shape.
/// </summary>
public sealed record RunRequest(string? Project);
