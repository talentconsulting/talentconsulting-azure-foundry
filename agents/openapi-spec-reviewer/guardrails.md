# Guardrails

## Data Access

- Use only the supplied input payload.
- Do not inspect repositories.
- Do not follow external links.
- Do not use cached information.

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

- Return only valid JSON matching the configured schema.
- Do not include markdown.
- Do not include the full OpenAPI YAML in the response.
- Do not include secrets, credentials, connection strings, or environment variable values.
- Do not include stack traces or raw tool output.
- Do not include additional JSON properties.
