# Evaluations

## Evaluation 1: Create one file

### Input

```json
{
  "changes": [
    {
      "filename": "accounts-api-openapi.json",
      "content": "{\n  \"openapi\": \"3.1.0\",\n  \"info\": {\n    \"title\": \"Accounts API\",\n    \"version\": \"3.1.0\"\n  },\n  \"paths\": {}\n}\n",
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
- Write `openapi/accounts-api-openapi.json` to the branch.
- Commit the file change to the branch.
- Create one pull request into the default branch.
- Return `success: true` with the commit SHA, pull request URL, and file action.

## Evaluation 2: Create multiple files in one repository

### Input

```json
{
  "changes": [
    {
      "filename": "accounts-api-openapi.json",
      "content": "{\n  \"openapi\": \"3.1.0\",\n  \"info\": {\n    \"title\": \"Accounts API\",\n    \"version\": \"3.1.0\"\n  },\n  \"paths\": {}\n}\n",
      "repository": "TalentConsulting/example-api",
      "path": "openapi"
    },
    {
      "filename": "employer-api-openapi.json",
      "content": "{\n  \"openapi\": \"3.1.0\",\n  \"info\": {\n    \"title\": \"Employer API\",\n    \"version\": \"3.1.0\"\n  },\n  \"paths\": {}\n}\n",
      "repository": "TalentConsulting/example-api",
      "path": "openapi"
    }
  ]
}
```

### Expected Behaviour

- Create one branch.
- Write both files to that branch.
- Commit both file changes to the branch, preferably in one commit.
- Create one pull request.
- Return both file paths in `filesWritten`.

## Evaluation 3: Create files from workflow OpenAPI generator output

### Input

```json
{
  "repository": "https://github.com/TalentConsulting/example-api",
  "path": "openapi-specs",
  "openApiGeneratorResponse": {
    "specs": [
      {
        "domain-api": "accounts-api",
        "open-api": {
          "openapi": "3.1.0",
          "info": {
            "title": "Accounts API",
            "version": "3.1.0"
          },
          "paths": {
            "/accounts": {
              "get": {
                "responses": {
                  "200": {
                    "description": "OK"
                  }
                }
              }
            }
          }
        },
        "fileName": "accounts-api-openapi.json",
        "serviceName": "Accounts API",
        "sourcePath": ".",
        "contentType": "application/json"
      }
    ]
  }
}
```

### Expected Behaviour

- Derive one file change from `openApiGeneratorResponse.specs`.
- Create one branch.
- Write `openapi-specs/accounts-api-openapi.json`.
- Commit the file change to the branch.
- Create one pull request.

## Evaluation 4: Reject multiple repositories

### Input

```json
{
  "changes": [
    {
      "filename": "accounts-api-openapi.json",
      "content": "{\n  \"openapi\": \"3.1.0\"\n}\n",
      "repository": "TalentConsulting/accounts-api",
      "path": "openapi"
    },
    {
      "filename": "employer-api-openapi.json",
      "content": "{\n  \"openapi\": \"3.1.0\"\n}\n",
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
  "commitSha": "",
  "pullRequestUrl": "",
  "pullRequestNumber": 0,
  "filesWritten": [],
  "errors": [
    "All changes must target the same repository."
  ]
}
```

## Evaluation 5: Reject unsafe path

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

## Evaluation 6: No changed content

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
- Do not create a commit when no file content changed.
- Return `success: false`.
- Include the target path with action `unchanged`.
- Include an error explaining that there were no content changes to propose.

## Evaluation Checks

The response must:

- Be valid JSON.
- Match the configured schema.
- Contain no markdown.
- Contain no additional properties.
- Always include `success`, `repository`, `branchName`, `commitSha`, `pullRequestUrl`, `pullRequestNumber`, `filesWritten`, and `errors`.
