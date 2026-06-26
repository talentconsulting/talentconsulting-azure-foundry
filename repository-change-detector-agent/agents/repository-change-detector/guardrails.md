# Guardrails

## Data Access

- Only access the manifest repository provided in `manifestRepository`.
- Only access repository URLs listed in the manifest.
- Do not inspect unrelated repositories.
- Do not use cached data when checking latest commits.

## Write Safety

This agent is read-only.

The agent must not:

- Create files
- Update files
- Delete files
- Create branches
- Create pull requests
- Merge pull requests
- Modify repository settings
- Trigger deployments

## Output Safety

- Return only the configured JSON output.
- Do not include secrets, tokens, environment variables, or internal tool logs.
- Do not include stack traces or raw tool error output.
- Do not include additional diagnostic fields unless the schema is explicitly changed.

## Failure Behaviour

If the manifest cannot be read, return:

```json
{
  "repositories": []
}
```

If an individual repository cannot be checked, include that repository in the output using the manifest `repoName` and `repoURL`.

This allows downstream agents or workflows to decide whether to retry, skip, or raise a validation issue.
