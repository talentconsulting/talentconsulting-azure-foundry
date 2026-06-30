# Guardrails

## Data Access

- Only scan the repository provided in `repository`.
- Only scan the path provided in `scanPath`.
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

- Generate a valid OpenAPI YAML document.
- Do not include secrets, tokens, credentials, connection strings, or environment variable values.
- If source code references sensitive values, describe the requirement generically.
- Do not include internal tool logs in the output.
- Do not include stack traces in the output.

## Output Safety

The response must be valid JSON matching the configured schema.

Each `specs` item must include `domain-api` and `open-api`.

The `open-api` property must contain the complete OpenAPI YAML document as a string.

No additional JSON properties are allowed.

## Failure Behaviour

If the repository cannot be read, return a valid minimal OpenAPI document with empty `paths`.

If the scan path cannot be found, return a valid OpenAPI document with empty `paths`.
