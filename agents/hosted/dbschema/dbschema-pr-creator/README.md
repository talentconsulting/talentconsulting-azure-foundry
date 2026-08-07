# Database Schema PR Creator

A hosted Foundry agent that commits validated database-schema JSON files and an optional updated manifest to one GitHub branch, then opens one pull request. It never approves or merges the pull request.

## Input

```json
{
  "repository": "owner/schema-catalogue",
  "schemas": [
    {
      "sourceUrl": "https://github.com/owner/application/tree/main/src/Data",
      "schema": {
        "database": {"name": "application", "engine": null},
        "tables": [{"name": "orders"}],
        "types": []
      },
      "targetPath": "application/db-schema/database.schema.json"
    }
  ],
  "baseBranch": "main",
  "manifestFile": {"path": "manifest.json", "content": []}
}
```

`repository` and a non-empty `schemas` array are required. Every schema requires its original GitHub tree `sourceUrl`, the generated `schema`, and a safe JSON `targetPath`. Optional fields are `baseBranch`, `branchName`, `pullRequestTitle`, `pullRequestBody`, and `manifestFile`.

The agent accepts at most 100 schemas and 10 MiB of generated JSON per request. Unchanged files do not create a branch or pull request.

## GitHub connection

The agent reuses the Foundry **Custom keys** connection named `openapi-pr-github`, whose secret field is `github_token`. The hosted agent maps that write-only value to `GITHUB_PR_TOKEN`. The token needs repository contents and pull-request write access to the destination repository.

## Test and deploy

```bash
python3 -m unittest discover -s src/dbschema-pr-creator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy dbschema-pr-creator --no-prompt
```

The root workflow `.github/workflows/deploy-dbschema-pr-creator.agent.yml` performs the same deployment using the `dev` GitHub environment. The shared `openapi-pr-github` connection must already exist in the target Foundry project.
