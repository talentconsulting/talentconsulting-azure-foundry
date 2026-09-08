# .NET Version Generator

Deterministically parses a bounded bundle of `.csproj` and `global.json` files -- downloaded directly from the source repository, not passed as content -- into a validated .NET version catalog. No model is used: `TargetFramework`/`TargetFrameworks` (and the legacy `TargetFrameworkVersion`) are read directly from each `.csproj`'s XML, and `sdk.version`/`sdk.rollForward` are read directly from each `global.json`'s JSON. Each distinct target framework moniker found across `projects` is also looked up in a hardcoded end-of-support table and reported as `dotnetSupport`.

## Input

```json
{
  "sourceUrl": "https://github.com/owner/repository/tree/main/src",
  "sourceFiles": [
    "https://github.com/owner/repository/blob/main/src/App/App.csproj",
    "https://github.com/owner/repository/blob/main/src/global.json"
  ]
}
```

`sourceFiles` accepts 1-100 blob URLs, all belonging to the same repository and ref as `sourceUrl`.

## Output

```json
{
  "repository": "owner/repository",
  "ref": "main",
  "path": "src",
  "projects": [
    {"path": "src/App/App.csproj", "targetFrameworks": ["net8.0"]}
  ],
  "sdks": [
    {"path": "src/global.json", "version": "8.0.100", "rollForward": "latestMinor"}
  ],
  "dotnetSupport": [
    {"targetFramework": "net8.0", "endOfSupport": "2026-11-10", "supportPhase": "LTS"}
  ]
}
```

A `.csproj` with no recognizable target framework element is still included, with an empty `targetFrameworks` array -- a valid, successful outcome, not a failure. A `global.json` with no `sdk` key is omitted from `sdks` entirely.

`dotnetSupport` has one deduplicated entry per distinct `targetFrameworks` moniker found across `projects` (a moniker used by several projects still yields a single entry). It is a static, hardcoded lookup table in `generator.py`, not a live query -- Microsoft ships a new .NET version and updates support dates roughly once a year (each November), so the table needs manual maintenance and can go stale if not updated. It only covers modern .NET (`net5.0` onward) and .NET Core (`netcoreapp1.0`-`netcoreapp3.1`) monikers; .NET Framework monikers (`net48`, `net472`, ...) and .NET Standard monikers (`netstandard2.0`, ...) always come back with `endOfSupport: null, supportPhase: null` -- deliberately, since .NET Framework support tracks the host Windows OS lifecycle rather than a fixed date of its own, and .NET Standard is a spec, not a runtime with its own support lifecycle.

## Safety and limits

At most 100 source files, 512 KiB per file, and 2 MiB combined. Non-UTF-8 files fail the request. Errors are returned as `{"error": {"code", "message"}}`.

## Test

```bash
python3 -m unittest discover -s src/repo-metadata-generator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy repo-metadata-generator --no-prompt
```
