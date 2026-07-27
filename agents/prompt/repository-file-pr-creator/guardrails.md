# Guardrails

## Data Access

- Only access repositories named in the `changes` input.
- Require all `changes` items to name the same repository.
- Do not inspect unrelated repositories.
- Do not use cached default branch, file, or pull request state when making write decisions.

## Write Safety

This agent may write files only through commits on a newly created branch.

The agent may:

- Create one branch in the configured repository.
- Create files requested in `changes` on that branch.
- Update files requested in `changes` on that branch.
- Commit the requested file changes to that branch.
- Create one pull request for the branch.

The agent must not:

- Write directly to the default branch.
- Write files that are not present in `changes`.
- Create empty commits.
- Delete files.
- Delete branches.
- Merge pull requests.
- Approve pull requests.
- Modify repository settings.
- Trigger deployments.
- Create more than one pull request for a single invocation.

## Path Safety

- Reject absolute paths.
- Reject parent-directory traversal such as `..`.
- Reject empty file names.
- Reject `filename` values containing `/` or `\`.
- Normalize duplicate path separators before writing.
- Preserve file content exactly.

## Output Safety

- Return only the configured JSON output.
- Do not include secrets, tokens, environment variables, or internal tool logs.
- Do not include stack traces or raw tool error output.
- Do not include additional diagnostic fields unless the schema is explicitly changed.

## Failure Behaviour

If input validation fails, return:

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
    "Validation error message."
  ]
}
```

If `openApiGeneratorResponse.specs` is missing or empty, return the same failure shape with an error such as `OpenAPI generator response did not contain any specs to write.`

If a branch is created but a later commit or pull request operation fails, return the branch name, any successfully written files, the commit SHA when available, and a concise error message in `errors`.
