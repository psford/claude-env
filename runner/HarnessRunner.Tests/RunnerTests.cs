using System.Net;
using System.Net.Sockets;
using System.Net.Http.Json;
using System.Text.Json;
using HarnessRunner;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Hosting;
using Xunit;

namespace HarnessRunner.Tests;

/// <summary>
/// CH-186. These run in WSL on purpose and that is not a dodge: the runner
/// targets net8.0, so Kestrel binding, the allowlist refusal, the request shape
/// and exit-code passthrough are the same code here as on Windows. The one
/// thing that genuinely needs Windows -- building a net8.0-windows project -- is
/// AC7, and it is manual because nothing in WSL can start a Windows process.
/// </summary>
public class RunnerFixture : IDisposable
{
    public string Dir { get; }
    public string AllowlistPath { get; }

    public RunnerFixture()
    {
        Dir = Path.Combine(Path.GetTempPath(), "hr-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Dir);
        var here = Path.GetDirectoryName(typeof(RunnerFixture).Assembly.Location)!;
        var testdata = Path.GetFullPath(Path.Combine(here, "..", "..", "..", "..", "testdata"));
        AllowlistPath = Path.Combine(Dir, "projects.json");
        File.WriteAllText(AllowlistPath, JsonSerializer.Serialize(new[]
        {
            new { key = "good", solution = Path.Combine(testdata, "GoodProject", "GoodProject.csproj") },
            new { key = "bad", solution = Path.Combine(testdata, "BadProject", "BadProject.csproj") },
            new { key = "missing", solution = Path.Combine(testdata, "NoSuchProject", "Nope.csproj") },
        }));
    }

    public void Dispose() { try { Directory.Delete(Dir, true); } catch { } }
}

public class RunnerTests : IClassFixture<RunnerFixture>
{
    private readonly RunnerFixture _fx;
    public RunnerTests(RunnerFixture fx) => _fx = fx;

    /// <summary>The real service on an ephemeral loopback port -- never 8919, so a
    /// test run cannot collide with a runner Patrick actually started.</summary>
    /// <summary>The REAL app on an ephemeral loopback port -- never 8919, so a
    /// test run cannot collide with a runner Patrick actually started.</summary>
    private async Task<(WebApplication app, HttpClient http, int port)> StartAsync(string host = "127.0.0.1")
    {
        var port = FreePort();
        var app = RunnerApp.Build(_fx.AllowlistPath, port, host);
        await app.StartAsync();
        return (app, new HttpClient { BaseAddress = new Uri($"http://127.0.0.1:{port}") }, port);
    }

    private static int FreePort()
    {
        using var l = new TcpListener(IPAddress.Loopback, 0);
        l.Start();
        var p = ((IPEndPoint)l.LocalEndpoint).Port;
        l.Stop();
        return p;
    }

    // -- AC1 ---------------------------------------------------------------
    [Fact]
    public async Task It_listens_on_loopback_only()
    {
        // Both halves in one test on purpose: a refused non-loopback connect
        // proves nothing unless the loopback connect is shown green at the same
        // moment on the same port.
        var (app, http, port) = await StartAsync();
        try
        {
            Assert.Equal(HttpStatusCode.OK, (await http.GetAsync("/health")).StatusCode);

            var lan = LocalNonLoopback();
            Assert.True(lan is not null,
                "no non-loopback IPv4 on this machine, so the exclusion cannot be demonstrated");

            // A refused connection is the PASS here, and it arrives as an
            // exception rather than a false return -- letting it propagate would
            // fail the test on the very outcome it is looking for.
            bool reachable;
            try
            {
                using var probe = new TcpClient();
                reachable = probe.ConnectAsync(lan!, port).Wait(TimeSpan.FromSeconds(2))
                            && probe.Connected;
            }
            catch (Exception ex) when (ex is SocketException or AggregateException)
            {
                reachable = false;
            }
            Assert.False(reachable,
                $"the runner accepted a connection on {lan}:{port}; it must bind 127.0.0.1 only");
        }
        finally { await app.StopAsync(); }
    }

    private static IPAddress? LocalNonLoopback() =>
        Dns.GetHostAddresses(Dns.GetHostName())
           .FirstOrDefault(a => a.AddressFamily == AddressFamily.InterNetwork
                                && !IPAddress.IsLoopback(a));

    // -- AC2 ---------------------------------------------------------------
    [Fact]
    public async Task Health_reports_the_allowlist_it_actually_read()
    {
        var (app, http, _) = await StartAsync();
        try
        {
            var body = await http.GetFromJsonAsync<JsonElement>("/health");
            var projects = body.GetProperty("projects").EnumerateArray()
                               .Select(e => e.GetString()).ToList();
            // Against the FIXTURE allowlist, so this checks a real read rather
            // than a hardcoded constant.
            Assert.Equal(new[] { "bad", "good", "missing" }, projects);
            Assert.NotEmpty(body.GetProperty("sdks").EnumerateArray());
        }
        finally { await app.StopAsync(); }
    }

    // -- AC3 ---------------------------------------------------------------
    [Theory]
    [InlineData("nope")]
    [InlineData("")]
    [InlineData("GOOD")]   // case-differing key is a typo, not a match
    public async Task An_unregistered_key_is_refused_and_starts_nothing(string key)
    {
        var (app, http, _) = await StartAsync();
        try
        {
            var started = DateTime.UtcNow;
            var res = await http.PostAsJsonAsync("/build", new { project = key });
            Assert.Equal(HttpStatusCode.BadRequest, res.StatusCode);
            Assert.Contains("good", await res.Content.ReadAsStringAsync());
            // A refusal that took as long as a build would mean something ran.
            Assert.True(DateTime.UtcNow - started < TimeSpan.FromSeconds(3),
                        "the refusal took long enough that a build may have started");
        }
        finally { await app.StopAsync(); }
    }

    // -- AC5 ---------------------------------------------------------------
    [Fact]
    public async Task A_failing_build_is_http_200_carrying_the_real_exit_code()
    {
        // The PAIR matters: proving only the failure case is satisfied by an
        // implementation that always returns non-zero.
        var (app, http, _) = await StartAsync();
        try
        {
            var bad = await http.PostAsJsonAsync("/build", new { project = "bad" });
            Assert.Equal(HttpStatusCode.OK, bad.StatusCode);
            var badBody = await bad.Content.ReadFromJsonAsync<JsonElement>();
            Assert.NotEqual(0, badBody.GetProperty("exit_code").GetInt32());
            Assert.Contains("error", badBody.GetProperty("stdout").GetString()!,
                            StringComparison.OrdinalIgnoreCase);

            var good = await http.PostAsJsonAsync("/build", new { project = "good" });
            var goodBody = await good.Content.ReadFromJsonAsync<JsonElement>();
            Assert.Equal(0, goodBody.GetProperty("exit_code").GetInt32());
        }
        finally { await app.StopAsync(); }
    }

    [Fact]
    public async Task A_registered_solution_that_is_missing_says_so_distinctly()
    {
        var (app, http, _) = await StartAsync();
        try
        {
            var res = await http.PostAsJsonAsync("/build", new { project = "missing" });
            Assert.Equal(HttpStatusCode.OK, res.StatusCode);
            var body = await res.Content.ReadFromJsonAsync<JsonElement>();
            var stderr = body.GetProperty("stderr").GetString()!;
            Assert.Contains("not found", stderr);
            // Distinguishable from a compile failure: the caller acts differently.
            Assert.DoesNotContain("error CS", stderr);
        }
        finally { await app.StopAsync(); }
    }
}
