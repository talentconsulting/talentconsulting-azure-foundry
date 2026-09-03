# .NET Version Manifest Orchestrator

Reads a shared public GitHub manifest, selects only `dotnet-version` nodes, compares branch-head commits, runs complete deferred dotnet-version workflows, and publishes generated target-framework and SDK-version catalogs plus updated commit hashes in one pull request. A repository whose workflow finds zero `.csproj`/`global.json` files is a valid, successful outcome.

```json
{"sourceUrl":"https://github.com/talentconsulting/service-catalogue-data/blob/main/manifest.json"}
```

Manifest node:

```json
{
  "dotnet-version": {
    "path-to-scan": "tree/main/src",
    "last-commit-hash-scanned": ""
  }
}
```

```bash
python3 -m unittest discover -s src/dotnet-version-manifest-orchestrator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy dotnet-version-manifest-orchestrator --no-prompt
```
