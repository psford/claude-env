using System.Reflection;
using System.Text.RegularExpressions;
using HarnessRunner;
using Xunit;

namespace HarnessRunner.Tests;

/// <summary>
/// The two constraints that are the whole reason this runner is allowed to
/// exist. Both are guards against a future well-meaning "improvement" rather
/// than against today's code -- today's code is correct, and that is exactly
/// when a constraint is easiest to erode without anyone noticing.
/// </summary>
public class ConstraintTests
{
    private static string RepoRoot()
    {
        var dir = Path.GetDirectoryName(typeof(ConstraintTests).Assembly.Location)!;
        while (!Directory.Exists(Path.Combine(dir, ".git")))
        {
            var parent = Directory.GetParent(dir)?.FullName
                ?? throw new InvalidOperationException("no repo root above the test assembly");
            dir = parent;
        }
        return dir;
    }

    /// <summary>
    /// Every file that could plausibly install or configure the runner.
    ///
    /// NOT just runner/: QA pointed out that an install.ps1 or a runbook
    /// anywhere else in the repo could set the service to start on its own, and
    /// the scan would never look at it. Scanning the whole repo is cheap and the
    /// blast radius of missing one is the loss of this design's only control.
    /// </summary>
    private static IEnumerable<string> SourceFiles() =>
        Directory.EnumerateFiles(RepoRoot(), "*.*", SearchOption.AllDirectories)
                 .Where(f => !f.Contains($"{Path.DirectorySeparatorChar}.git{Path.DirectorySeparatorChar}"))
                 .Where(f => f.EndsWith(".cs") || f.EndsWith(".csproj") || f.EndsWith(".ps1"))
                 .Where(f => !f.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}")
                          && !f.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}")
                          // This file names the forbidden strings in order to
                          // forbid them; a guard cannot check for a word it may
                          // not write down.
                          && !f.EndsWith("ConstraintTests.cs"));

    // -- AC4 ---------------------------------------------------------------
    [Fact]
    public void The_request_carries_a_key_and_nothing_that_could_become_a_command()
    {
        // A field-name allowlist rather than a blocklist: a NEW field breaks the
        // build until someone justifies it, which is the direction that fails
        // safe. A blocklist only catches the names we thought of.
        var props = typeof(RunRequest).GetProperties(BindingFlags.Public | BindingFlags.Instance)
                                      .Select(p => p.Name).ToArray();
        Assert.Equal(new[] { "Project" }, props);
    }

    [Fact]
    public void No_process_is_started_from_a_concatenated_command_line()
    {
        // A string command line is re-parsed by the shell, which is where a
        // quoting bug turns one path into two arguments and, occasionally, into
        // a second command. ArgumentList is the shape that cannot do that.
        foreach (var file in SourceFiles().Where(f => f.EndsWith(".cs")))
        {
            var text = File.ReadAllText(file);
            Assert.False(Regex.IsMatch(text, @"Arguments\s*="),
                $"{Path.GetFileName(file)} sets ProcessStartInfo.Arguments as a string; " +
                "use ArgumentList so nothing is re-parsed");
            if (text.Contains("ProcessStartInfo"))
            {
                Assert.Contains("UseShellExecute = false", text);
            }
        }
    }

    // -- AC8 ---------------------------------------------------------------
    [Fact]
    public void Nothing_makes_the_runner_start_without_Patrick()
    {
        // The control this whole epic rests on. A Manual-start Windows service
        // is FINE and is the intended shape -- installed, off at boot, up on
        // Start-Service. What is forbidden is anything that starts it without a
        // person deciding to: automatic startup, a Run key, a Startup shortcut,
        // a scheduled task.
        //
        // Written as a repository scan rather than a comment because the
        // realistic way this control disappears is somebody helpfully making the
        // runner "always available" months from now.
        // Both spellings. QA found the first version matched only `=` forms, so
        // `New-Service -StartupType Automatic` -- the way PowerShell actually
        // writes it, and the way an install script would -- sailed through with
        // the whole suite green.
        //
        // Scanned over code and SCRIPTS, not .md: the runbook explains this rule
        // and necessarily quotes the forbidden strings to do so. Prose describing
        // a constraint is not a mechanism for breaking it, and a guard that
        // cannot tell those apart forces the documentation to go vague.
        string[] forbidden =
        {
            "StartupType=Automatic", "StartupType = Automatic",
            "-StartupType Automatic", "-StartupType AutomaticDelayedStart",
            "StartupType=AutomaticDelayedStart",
            "start=auto", "start= auto",
            "CurrentVersion\\\\Run", "Register-ScheduledTask", "schtasks",
            "Startup\\\\", ".lnk",
        };
        Assert.NotEmpty(forbidden);
        foreach (var file in SourceFiles())
        {
            var text = File.ReadAllText(file);
            // Only files that MENTION the runner. Scanning the whole repo blindly
            // flagged deploy-app.ps1 for containing ".lnk" -- an unrelated script
            // that has nothing to do with this service. A file can only make THE
            // RUNNER start on its own if it names it, and a guard that cries wolf
            // on unrelated code is one someone eventually deletes.
            if (!text.Contains("HarnessRunner", StringComparison.OrdinalIgnoreCase))
                continue;
            foreach (var bad in forbidden)
            {
                Assert.False(text.Contains(bad, StringComparison.OrdinalIgnoreCase),
                    $"{Path.GetFileName(file)} contains '{bad}'. The runner must not start " +
                    "without Patrick -- a Manual-start service is the intended shape, and " +
                    "anything that starts it on its own removes the only control this design has.");
            }
        }
    }

    [Fact]
    public void The_scan_actually_reads_files()
    {
        // Instrument check: the scan is vacuous over an empty file set, and one
        // careless edit to the filter makes it so. QA noted the previous version
        // of this test asserted nothing about the needle list either -- that is
        // now asserted inside the scan itself, where the list lives.
        var files = SourceFiles().ToList();
        Assert.True(files.Count > 5, $"the scan found only {files.Count} files");
        Assert.Contains(files, f => f.EndsWith("RunnerApp.cs"));
        // Reaches OUTSIDE runner/, which is the gap QA found: an install script
        // anywhere else in the repo could set the service to start on its own.
        Assert.Contains(files, f => !f.Contains($"{Path.DirectorySeparatorChar}runner{Path.DirectorySeparatorChar}"));
    }
}
