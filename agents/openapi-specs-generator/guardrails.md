# Guardrails

## Data Access

- Scan only the repository supplied in `repository`.
- Scan only the directory supplied in `scanPath`.
- Use the repository default branch for reads.
- Do not inspect unrelated repositories.
- Do not follow external links unless they are repository-local references required to understand API code.

## Read Only

This agent is read-only.

It must never:

- Create files
- Update files
- Delete files
- Create branches
- Create pull requests
- Merge pull requests
- Modify repository settings
- Trigger deployments

## Output Safety

- Return only valid JSON.
- Do not return markdown.
- Do not return explanations.
- Do not return tool logs.
- Do not return stack traces.
- Do not return secrets, credentials, tokens, connection strings, or environment variable values.

## OpenAPI Safety

- Generate OpenAPI JSON objects, not YAML strings.
- Use OpenAPI `3.1.0`.
- Use conservative descriptions when exact behavior cannot be inferred.
- Include all discovered application endpoints.
- Ignore health, diagnostics, metrics, Swagger UI, and root redirects when application endpoints exist.
- Do not return only `/` and `/health` after reading a startup/program file if application route files exist elsewhere under `scanPath`.

## Failure Behaviour

If the repository cannot be read, the scan path cannot be found, or no API endpoints are discovered, return:

`{"specs":[]}`
