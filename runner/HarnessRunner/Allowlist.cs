using System.Text.Json;

namespace HarnessRunner;

/// <summary>One registered repository: a key, and the solution the runner may build.</summary>
public sealed record Project(string Key, string Solution);

/// <summary>
/// The set of solutions this runner will build, read from a file.
///
/// The file lives in the /mnt/c carve-out rather than beside the service, so WSL
/// can WRITE it and Windows can READ it. That is what makes registering a repo a
/// file write from the Linux side instead of a mutation endpoint on the service
/// -- and an endpoint that edits the allowlist would be a way to widen the
/// allowlist over HTTP, which is the one thing the allowlist exists to prevent.
///
/// What this list is and is not, stated here because it is the claim most likely
/// to be overstated later: it bounds WHICH REPOSITORY'S BUILD RUNS. It is not a
/// security boundary against hostile code. `dotnet build` executes that project's
/// MSBuild targets, and MSBuild targets run arbitrary code, so anything already
/// in a registered repo can do whatever it likes. What the list buys is that a
/// confused agent cannot point the runner at something destructive by accident,
/// and that the log says exactly which project ran.
/// </summary>
public sealed class Allowlist
{
    private readonly Dictionary<string, Project> _byKey;

    private Allowlist(IEnumerable<Project> projects) =>
        _byKey = projects.ToDictionary(p => p.Key, StringComparer.Ordinal);

    /// <summary>Registered keys, sorted, for /health and for refusal messages.</summary>
    public IReadOnlyList<string> Keys => _byKey.Keys.OrderBy(k => k, StringComparer.Ordinal).ToList();

    /// <summary>
    /// The project for `key`, or null. Case-SENSITIVE on purpose: a key differing
    /// only by case is a typo, and quietly accepting it would mean the log line
    /// and the request disagree about what ran.
    /// </summary>
    public Project? Find(string? key) =>
        key is not null && _byKey.TryGetValue(key, out var p) ? p : null;

    /// <summary>
    /// Read the file, or throw. A missing or malformed allowlist is fatal rather
    /// than an empty list: an empty list refuses every build with "not
    /// registered", which reads as a configuration someone chose. Refusing to
    /// start says what is actually wrong, once, where the person starting it is
    /// looking.
    /// </summary>
    public static Allowlist Load(string path)
    {
        if (!File.Exists(path))
            throw new InvalidOperationException(
                $"no allowlist at {path}. The runner builds only registered solutions, " +
                $"so it has nothing to do until one exists.");

        List<Project>? projects;
        try
        {
            projects = JsonSerializer.Deserialize<List<Project>>(
                File.ReadAllText(path),
                new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }
        catch (JsonException ex)
        {
            throw new InvalidOperationException($"{path} is not readable as an allowlist: {ex.Message}", ex);
        }

        if (projects is null || projects.Count == 0)
            throw new InvalidOperationException($"{path} registers no projects.");

        foreach (var p in projects)
        {
            if (string.IsNullOrWhiteSpace(p.Key) || string.IsNullOrWhiteSpace(p.Solution))
                throw new InvalidOperationException($"{path} has an entry missing a key or a solution.");
        }

        return new Allowlist(projects);
    }
}
