# Guardrails

## Data Access

- Only scan the repository provided in `repository`.
- Only scan the path provided in `scanPath`.
- Treat empty `scanPath`, `.`, and `./` as repository root and do not request a literal `.` path from GitHub.
- Do not inspect unrelated repositories.
- Do not follow external links unless they are repository-local references required to understand API code.

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

## OpenAPI Safety

- Generate a valid OpenAPI JSON document.
- Do not include secrets, tokens, credentials, connection strings, or environment variable values.
- If source code references sensitive values, describe the requirement generically.
- Do not include internal tool logs in the output.
- Do not include stack traces in the output.

## Output Safety

The response must be valid JSON matching the configured schema.

Each `specs` item must include `domain-api` and `open-api`.

The `open-api` property must contain the complete OpenAPI JSON document as an object, not as a string.

No additional JSON properties are allowed.

## Failure Behaviour

If the repository cannot be read, return:

```json
{
  "specs": []
}
```

If the scan path cannot be found, return:

```json
{
  "specs": []
}
```

Do not return refusal text, apology text, markdown, or prose.
