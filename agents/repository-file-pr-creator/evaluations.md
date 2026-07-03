# Evaluations

## Evaluation 1: Create one file

### Input

```json
{
  "changes": [
    {
      "filename": "accounts-api-openapi.yml",
      "content": "openapi: 3.1.0\ninfo:\n  title: Accounts API\n  version: 1.0.0\npaths: {}\n",
      "repository": "https://github.com/TalentConsulting/example-api",
      "path": "openapi"
    }
  ],
  "branchName": "ai-source-control/accounts-openapi",
  "pullRequestTitle": "Add Accounts OpenAPI specification"
}
```

### Expected Behaviour

- Create branch `ai-source-control/accounts-openapi` from the repository default branch.
- Write `openapi/accounts-api-openapi.yml` to the branch.
- Create one pull request into the default branch.
- Return `success: true` with the pull request URL and file action.

## Evaluation 2: Create multiple files in one repository

### Input

```json
{
  "changes": [
    {
      "filename": "accounts-api-openapi.yml",
      "content": "openapi: 3.1.0\ninfo:\n  title: Accounts API\n  version: 1.0.0\npaths: {}\n",
      "repository": "TalentConsulting/example-api",
      "path": "openapi"
    },
    {
      "filename": "employer-api-openapi.yml",
      "content": "openapi: 3.1.0\ninfo:\n  title: Employer API\n  version: 1.0.0\npaths: {}\n",
      "repository": "TalentConsulting/example-api",
      "path": "openapi"
    }
  ]
}
```

### Expected Behaviour

- Create one branch.
- Write both files to that branch.
- Create one pull request.
- Return both file paths in `filesWritten`.

## Evaluation 3: Reject multiple repositories

### Input

```json
{
  "changes": [
    {
      "filename": "accounts-api-openapi.yml",
      "content": "openapi: 3.1.0\n",
      "repository": "TalentConsulting/accounts-api",
      "path": "openapi"
    },
    {
      "filename": "employer-api-openapi.yml",
      "content": "openapi: 3.1.0\n",
      "repository": "TalentConsulting/employer-api",
      "path": "openapi"
    }
  ]
}
```

### Expected Output

```json
{
  "success": false,
  "repository": "",
  "branchName": "",
  "pullRequestUrl": "",
  "pullRequestNumber": 0,
  "filesWritten": [],
  "errors": [
    "All changes must target the same repository."
  ]
}
```

## Evaluation 4: Reject unsafe path

### Input

```json
{
  "changes": [
    {
      "filename": "secret.yml",
      "content": "value: test\n",
      "repository": "TalentConsulting/example-api",
      "path": "../.github/workflows"
    }
  ]
}
```

### Expected Behaviour

- Do not create a branch.
- Do not write any files.
- Do not create a pull request.
- Return `success: false` with a path validation error.

## Evaluation 5: No changed content

### Input

```json
{
  "changes": [
    {
      "filename": "README.md",
      "content": "# Existing content\n",
      "repository": "TalentConsulting/example-api",
      "path": "."
    }
  ]
}
```

### Repository State

The target file already contains exactly `# Existing content\n`.

### Expected Behaviour

- Do not create a pull request when no file content changed.
- Return `success: false`.
- Include the target path with action `unchanged`.
- Include an error explaining that there were no content changes to propose.

## Evaluation Checks

The response must:

- Be valid JSON.
- Match the configured schema.
- Contain no markdown.
- Contain no additional properties.
- Always include `success`, `repository`, `branchName`, `pullRequestUrl`, `pullRequestNumber`, `filesWritten`, and `errors`.
