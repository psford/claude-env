# Windows build runner

Builds and tests solutions WSL cannot. It exists because `dotnet build` on Linux
dies with `MSB4019` on any project targeting `net8.0-windows` — the WindowsDesktop
SDK is not there — and one Windows-only project takes the whole solution with it.

**It runs only when you start it.** That is the design, not an omission. See
"Why it is not automatic" below before changing it.

## First time: install it as a service

On Windows, from an elevated PowerShell:

```powershell
cd C:\Users\patri\Documents\claudeProjects\projects\claude-env\runner\HarnessRunner
dotnet publish -c Release -o C:\HarnessRunner

New-Service -Name HarnessRunner `
            -BinaryPathName "C:\HarnessRunner\HarnessRunner.exe" `
            -DisplayName "Harness build runner" `
            -StartupType Manual
```

`Manual` is the whole point: installed, **off at boot**, up only when you say so.

## Every session you want it

```powershell
Start-Service HarnessRunner      # or services.msc
Stop-Service  HarnessRunner
```

Check it from WSL:

```bash
curl -s http://127.0.0.1:8919/health
```

A 200 with the SDK list means it is up. Connection refused means it is not — and
`winbuild` reports that as its own thing rather than as a build failure.

## Registering a repository

The allowlist is a JSON file **in the carve-out**, so you can edit it from WSL:

```
/mnt/c/Users/patri/Documents/claudeProjects/projects/harness-runner-projects.json
```

```json
[
  { "key": "ttracker", "solution": "C:\\Users\\patri\\Documents\\claudeProjects\\projects\\T-Tracker_win\\TTracker.sln" }
]
```

One entry per repo you want buildable. Restart the service after editing.

Paths are **Windows** paths — the runner is a Windows process. The same file is
`/mnt/c/...` from WSL and `C:\...` from Windows; write the `C:\` form.

The allowlist lives here rather than beside the service so registering a repo is
a file write from Linux instead of an endpoint on the runner. An endpoint that
edited the allowlist would be a way to widen the allowlist over HTTP, which is
the one thing the allowlist exists to prevent.

## What the allowlist is, and is not

It bounds **which repository's build runs**. It is not a security boundary
against hostile code: `dotnet build` executes that project's MSBuild targets, and
MSBuild targets run arbitrary code, so anything already inside a registered repo
can do whatever it likes.

What it buys is that a confused agent cannot point the runner at something
destructive by accident, and that the log says exactly which project ran. Do not
describe it as sandboxing.

## Why it is not automatic

The trust boundary is already crossed: you run code this project writes every
time you paste a command into PowerShell. What a always-on daemon would change is
not *whether* arbitrary code can reach Windows, but *how often a person decides
it may*.

Manual start moves that decision from per-command to per-session, which is a
trade worth making. Automatic startup would remove it entirely — and it is the
only control this design has. A test fails the build if `StartupType=Automatic`,
a `Run` key, a Startup shortcut or a scheduled task appears in the repo.

## Endpoints

| | |
|---|---|
| `GET /health` | 200 with status, installed SDKs, registered keys |
| `POST /build` | `{"project":"<key>"}` |
| `POST /test` | `{"project":"<key>"}` |

A **failing build returns HTTP 200** carrying the real non-zero `exit_code`. An
HTTP error status would be indistinguishable from the runner being down, and
telling those two apart is the entire job of `winbuild` on the WSL side.

Requests carry a key and nothing else — no command, no arguments, no path.
