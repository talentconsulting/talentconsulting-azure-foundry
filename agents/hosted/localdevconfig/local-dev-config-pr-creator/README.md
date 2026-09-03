# Local Dev Config PR Creator

A hosted Foundry agent that commits validated local-development-configuration JSON catalogs and an optional updated manifest to one GitHub branch, then opens one pull request. It never approves or merges the pull request.

## Input

```json
{
  "repository": "owner/local-dev-config-catalogue",
  "catalogs": [
    {
      "sourceUrl": "https://github.com/owner/application/tree/main/src",
      "catalog": {
        "repository": "owner/application",
        "ref": "main",
        "path": "src",
        "localServices": [
          {
            "name": "PostgreSQL",
            "kind": "database",
            "technology": "postgresql",
            "configurationKeys": ["DATABASE_URL"],
            "evidence": [{"sourceFile": "src/docker-compose.yml", "reason": "postgres service defined"}]
          }
        ],
        "configurationKeys": [
          {"key": "DATABASE_URL", "sourceFile": "src/.env.example", "reason": "PostgreSQL connection string"}
        ]
      },
      "targetPath": "application/local-dev-config/local-dev-config.json"
    }
  ],
  "baseBranch": "main",
  "manifestFile": {"path": "manifest.json", "content": []}
}
```

`repository` and a non-empty `catalogs` array are required. Every catalog requires its original GitHub tree `sourceUrl`, the generated `catalog` (with `repository`, `ref`, `path`, `localServices`, and `configurationKeys`), and a safe JSON `targetPath`. When `targetPath` is omitted it defaults to `{sourceRepoName}/{targetDirectory or "local-dev-config"}/local-dev-config.json` — the source repository name comes first, then the target directory. Optional fields are `targetDirectory`, `baseBranch`, `branchName`, `pullRequestTitle`, `pullRequestBody`, and `manifestFile`.

The agent accepts at most 100 catalogs and 10 MiB of generated JSON per request. Unchanged files do not create a branch or pull request.

## GitHub connection

The agent reuses the Foundry **Custom keys** connection named `openapi-pr-github`, whose secret field is `github_token`. The hosted agent maps that write-only value to `GITHUB_PR_TOKEN`. The token needs repository contents and pull-request write access to the destination repository.

## Test and deploy

```bash
python3 -m unittest discover -s src/local-dev-config-pr-creator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy local-dev-config-pr-creator --no-prompt
```

The root workflow `.github/workflows/deploy-local-dev-config-pr-creator.agent.yml` performs the same deployment using the `dev` GitHub environment. The shared `openapi-pr-github` connection must already exist in the target Foundry project.
