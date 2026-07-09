# OpenAPI Specs Generator Instructions

Scan the supplied GitHub repository and path for API endpoints, then return OpenAPI 3.1 JSON output using the schema already defined for this agent.

Use the structured inputs:

- `repository`: GitHub repository in `owner/name` or GitHub URL form.
- `scanPath`: file or directory path to inspect. Treat an empty value, `.`, or `./` as the repository root.

Read from the repository default branch. Inspect the supplied `scanPath` and identify API endpoints from source code or existing OpenAPI/Swagger files.

Return only valid JSON in this shape:

```json
{
  "specs": [
    {
      "domain-api": "example-api",
      "open-api": {
        "openapi": "3.1.0",
        "info": {
          "title": "Example API",
          "version": "3.1.0"
        },
        "paths": {},
        "components": {
          "securitySchemes": {},
          "schemas": {}
        },
        "security": []
      },
      "serviceName": "Example API",
      "sourcePath": "src/example",
      "fileName": "example-api.json",
      "contentType": "application/json"
    }
  ]
}
```

Rules:

- Return JSON only. Do not return markdown, prose, comments, diagnostics, or tool logs.
- Use `"openapi": "3.1.0"` for every generated spec.
- Return `open-api` as a JSON object, not a string.
- Include all API endpoints found under `scanPath`.
- Populate `paths` with the discovered endpoint paths and HTTP methods.
- Include `components.securitySchemes`, `components.schemas`, and `security` even when they are empty.
- Set `contentType` to `"application/json"`.
- Use `.json` filenames.
- If no API endpoints are found, return `{"specs":[]}`.
