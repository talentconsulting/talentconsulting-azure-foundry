# Repository Metadata Generator

Deterministically parses a bounded bundle of `.csproj`, `global.json`, `.bicep`, and `.tf` files -- downloaded directly from the source repository, not passed as content -- into a validated repo-metadata catalog. No model is used: `TargetFramework`/`TargetFrameworks` (and the legacy `TargetFrameworkVersion`) are read directly from each `.csproj`'s XML, `sdk.version`/`sdk.rollForward` are read directly from each `global.json`'s JSON, and Azure resource `type`/`name` pairs are read directly from each `.bicep`/`.tf` file's source text via regex and brace-depth matching (no Bicep/Terraform compiler or live Azure query is involved).

## Input

```json
{
  "sourceUrl": "https://github.com/owner/repository/tree/main/src",
  "sourceFiles": [
    "https://github.com/owner/repository/blob/main/src/App/App.csproj",
    "https://github.com/owner/repository/blob/main/src/global.json",
    "https://github.com/owner/repository/blob/main/src/infra/main.bicep"
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
  "lastCommitDate": "2024-01-01T00:00:00Z",
  "projects": [
    {"path": "src/App/App.csproj", "targetFrameworks": ["net8.0"]}
  ],
  "sdks": [
    {"path": "src/global.json", "version": "8.0.100", "rollForward": "latestMinor"}
  ],
  "azureResources": [
    {"path": "src/infra/main.bicep", "type": "Microsoft.Storage/storageAccounts", "name": "appstorage"}
  ]
}
```

A `.csproj` with no recognizable target framework element is still included, with an empty `targetFrameworks` array -- a valid, successful outcome, not a failure. A `global.json` with no `sdk` key is omitted from `sdks` entirely.

`azureResources` is populated from `resource` declarations in `.bicep` files (`Microsoft.*/...@apiVersion` types) and from `resource "azurerm_*" "..."` blocks in `.tf` files (non-`azurerm_` provider types, e.g. `aws_*`/`google_*`, are skipped). Only literal string names are resolved -- `name: '${var}-thing'` or `name = var.foo` (anything that isn't a plain quoted literal) comes back as `name: null`. `.bicepparam` files, ARM JSON templates, and Terraform `data` blocks are not parsed at all. Unlike `projects`/`sdks`, many `azureResources` entries can legitimately share the same `path`, since one IaC file commonly declares several resources.

## Safety and limits

At most 100 source files, 512 KiB per file, and 2 MiB combined. Non-UTF-8 files fail the request. Errors are returned as `{"error": {"code", "message"}}`.

## Test

```bash
python3 -m unittest discover -s src/repo-metadata-generator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy repo-metadata-generator --no-prompt
```
