# OpenAPI Spec PR Creator

A Python hosted agent that accepts generated OpenAPI specifications, writes them as deterministic JSON files in a configurable GitHub repository, and opens a pull request. It never approves or merges the pull request.

## Input

```json
{
  "repository": "owner/api-specifications",
  "specifications": [
    {
      "apiFile": "https://github.com/owner/source/blob/main/src/Api/BidsController.cs",
      "specification": {
        "openapi": "3.1.0",
        "info": {"title": "Bids API", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": {}}
      }
    }
  ],
  "targetDirectory": "openapi",
  "baseBranch": "main",
  "pullRequestTitle": "Update generated OpenAPI specifications"
}
```

`repository` and `specifications` are required. `repository` can be `owner/repository` or an HTTPS GitHub repository URL. The other properties are optional:

- `targetDirectory` defaults to `openapi`.
- `baseBranch` defaults to the destination repository's default branch.
- `branchName` defaults to a unique `openapi-specs/...` branch.
- `pullRequestTitle` and `pullRequestBody` have generated defaults.

For each source API, the agent preserves its source path beneath `targetDirectory` and changes the extension to `.openapi.json`.

## Output

The agent always returns JSON. A successful change includes the created pull request; identical files return `status: "unchanged"` without creating a branch or pull request.

```json
{
  "success": true,
  "status": "created",
  "repository": "owner/api-specifications",
  "branchName": "openapi-specs/20260803-120000-abc12345",
  "commitSha": "0123456789abcdef0123456789abcdef01234567",
  "pullRequestUrl": "https://github.com/owner/api-specifications/pull/12",
  "pullRequestNumber": 12,
  "filesWritten": [{"path": "openapi/src/Api/BidsController.openapi.json", "action": "created"}],
  "errors": []
}
```

## Authentication

Create a Foundry project **Custom keys** connection named `openapi-pr-github` with a secret field named `github_token`. The hosted agent resolves that write-only connection field into `GITHUB_PR_TOKEN` when its sandbox starts; the token is not stored in the agent definition.

For a fine-grained GitHub token, grant the destination repository:

- Contents: read and write
- Pull requests: read and write
- Metadata: read

The token is not accepted in the request body and is never returned. Ordinary azd environment substitution must not be used for the deployed token.

## Test and deploy

```bash
python3 -m unittest discover -s src/openapi-spec-pr-creator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy openapi-spec-pr-creator --no-prompt
```

The root workflow `.github/workflows/deploy-openapi-spec-pr-creator.agent.yml` performs the same deployment using the `dev` GitHub environment. The `openapi-pr-github` connection must already exist in the target Foundry project.
