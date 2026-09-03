# .NET Version Generator

Deterministically parses a bounded bundle of `.csproj` and `global.json` files -- downloaded directly from the source repository, not passed as content -- into a validated .NET version catalog. No model is used: `TargetFramework`/`TargetFrameworks` (and the legacy `TargetFrameworkVersion`) are read directly from each `.csproj`'s XML, and `sdk.version`/`sdk.rollForward` are read directly from each `global.json`'s JSON.

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
  ]
}
```

A `.csproj` with no recognizable target framework element is still included, with an empty `targetFrameworks` array -- a valid, successful outcome, not a failure. A `global.json` with no `sdk` key is omitted from `sdks` entirely.

## Safety and limits

At most 100 source files, 512 KiB per file, and 2 MiB combined. Non-UTF-8 files fail the request. Errors are returned as `{"error": {"code", "message"}}`.

## Test

```bash
python3 -m unittest discover -s src/dotnet-version-generator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy dotnet-version-generator --no-prompt
```
