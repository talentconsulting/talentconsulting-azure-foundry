# .NET Version PR Creator

A hosted Foundry agent that commits validated .NET version JSON catalogs and an optional updated manifest to one GitHub branch, then opens one pull request. It never approves or merges the pull request.

## Input

```json
{
  "repository": "owner/dotnet-version-catalogue",
  "catalogs": [
    {
      "sourceUrl": "https://github.com/owner/application/tree/main/src",
      "catalog": {
        "repository": "owner/application",
        "ref": "main",
        "path": "src",
        "projects": [
          {"path": "src/App/App.csproj", "targetFrameworks": ["net8.0"]}
        ],
        "sdks": [
          {"path": "src/global.json", "version": "8.0.100", "rollForward": "latestMinor"}
        ]
      },
      "targetPath": "application/dotnet-version/dotnet-version.json"
    }
  ],
  "baseBranch": "main",
  "manifestFile": {"path": "manifest.json", "content": []}
}
```

`repository` and a non-empty `catalogs` array are required. Every catalog requires its original GitHub tree `sourceUrl`, the generated `catalog` (with `repository`, `ref`, `path`, `projects`, and `sdks`), and a safe JSON `targetPath`. When `targetPath` is omitted it defaults to `{sourceRepoName}/{targetDirectory or "dotnet-version"}/dotnet-version.json` -- the source repository name comes first, then the target directory. Optional fields are `targetDirectory`, `baseBranch`, `branchName`, `pullRequestTitle`, `pullRequestBody`, and `manifestFile`.

The agent accepts at most 100 catalogs and 10 MiB of generated JSON per request. Unchanged files do not create a branch or pull request.

## GitHub connection

The agent reuses the Foundry **Custom keys** connection named `openapi-pr-github`, whose secret field is `github_token`. The hosted agent maps that write-only value to `GITHUB_PR_TOKEN`. The token needs repository contents and pull-request write access to the destination repository.

## Test and deploy

```bash
python3 -m unittest discover -s src/dotnet-version-pr-creator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy dotnet-version-pr-creator --no-prompt
```

The root workflow `.github/workflows/deploy-dotnet-version-pr-creator.agent.yml` performs the same deployment using the `dev` GitHub environment. The shared `openapi-pr-github` connection must already exist in the target Foundry project.
