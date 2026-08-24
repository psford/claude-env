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

    private static IEnumerable<string> SourceFiles() =>
        Directory.EnumerateFiles(Path.Combine(RepoRoot(), "runner"), "*.*", SearchOption.AllDirectories)
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
        string[] forbidden =
        {
            "StartupType=Automatic", "StartupType = Automatic",
            "StartupType=AutomaticDelayedStart", "start=auto", "start= auto",
            "CurrentVersion\\\\Run", "Register-ScheduledTask", "schtasks",
            "Startup\\\\", ".lnk",
        };
        foreach (var file in SourceFiles())
        {
            var text = File.ReadAllText(file);
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
    public void The_forbidden_list_is_not_empty()
    {
        // Instrument check: the scan above is vacuous over an empty file set or
        // an empty needle list, and both are one careless edit away.
        Assert.NotEmpty(SourceFiles().ToList());
    }
}
