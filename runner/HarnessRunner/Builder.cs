using System.Diagnostics;

namespace HarnessRunner;

/// <summary>What a build or test run produced.</summary>
public sealed record RunResult(int ExitCode, string Stdout, string Stderr, string Invocation);

/// <summary>
/// Runs `dotnet build` or `dotnet test` against a registered solution.
///
/// There is no path from a request to a command. The caller sends a KEY and a
/// VERB; the key resolves against the allowlist and the verb is one of two
/// constants. Nothing the caller sends reaches the process.
///
/// Started from an argument ARRAY with UseShellExecute=false, never a
/// concatenated string. A string command line is re-parsed by the shell, which
/// is where quoting bugs turn a path into two arguments and, occasionally, into
/// a second command.
/// </summary>
public static class Builder
{
    public static readonly IReadOnlyList<string> Verbs = new[] { "build", "test" };

    public static RunResult Run(string verb, Project project, string dotnet = "dotnet")
    {
        if (!Verbs.Contains(verb))
            throw new ArgumentException($"unknown verb '{verb}'", nameof(verb));

        // A missing solution is reported as its own thing rather than left to
        // surface as a build failure -- "the file is not there" and "the code
        // does not compile" are different problems and the caller acts on them
        // differently.
        if (!File.Exists(project.Solution))
            return new RunResult(
                ExitCode: -1,
                Stdout: "",
                Stderr: $"registered solution not found: {project.Solution}",
                Invocation: $"{verb} {project.Key}");

        var psi = new ProcessStartInfo
        {
            FileName = dotnet,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            WorkingDirectory = Path.GetDirectoryName(project.Solution)!,
        };
        psi.ArgumentList.Add(verb);
        psi.ArgumentList.Add(project.Solution);

        using var proc = Process.Start(psi)
            ?? throw new InvalidOperationException($"could not start {dotnet}");
        var stdout = proc.StandardOutput.ReadToEnd();
        var stderr = proc.StandardError.ReadToEnd();
        proc.WaitForExit();

        return new RunResult(proc.ExitCode, stdout, stderr,
                             $"{verb} {project.Key} -> {dotnet} {verb} {project.Solution}");
    }
}
