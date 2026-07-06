# OpenAPI Specs Generator Instructions

## Purpose

Scan a GitHub repository path and generate OpenAPI 3.1 JSON specifications for every API endpoint discovered under that path.

The response must be a JSON object with a `specs` array. Each item in `specs` represents one detected API/domain/service and contains a complete OpenAPI JSON object.

---

# Inputs

The agent receives:

| Input | Description | Example |
| --- | --- | --- |
| `repository` | GitHub repository to scan in `owner/name` form or GitHub URL form | `org/example-api` |
| `scanPath` | Directory within the repository to scan | `src` |

Use only the current structured input for this invocation. Ignore prior workflow messages, prior agent outputs, and conversation history when deciding what to return.

Treat an empty `scanPath`, `.`, or `./` as the repository root. Do not call GitHub file-content tools with a literal `.` path.

Resolve the repository default branch before reading files. Read from the repository default branch only. Do not assume the default branch is named `main`, `master`, `develop`, or `dev`.

---

# Required Output

Return only valid JSON matching this shape:

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
        "security": [
          {
            "BearerAuth": []
          }
        ]
      },
      "serviceName": "Example API",
      "sourcePath": "src/Example.Api",
      "fileName": "example-api.json",
      "contentType": "application/json"
    }
  ]
}

The response must start with `{` and end with `}`. Do not wrap the response in markdown. Do not include prose, comments, diagnostics, or tool output.

If no API endpoints are discovered, return:

`{"specs":[]}`

---

# Scan Rules

Scan the entire `scanPath` recursively before generating the response.

First build a repository file inventory for the full `scanPath`. Do not generate a response from only `Program.cs`, startup files, root files, or the first directory listing.

After building the file inventory, search all candidate API files before returning. Candidate API files include:

- `**/Controllers/**/*.cs`
- `**/*Controller.cs`
- `**/Endpoints/**/*.cs`
- `**/*Endpoints.cs`
- `**/*Routes.cs`
- `**/Functions/**/*.cs`
- files containing `[HttpGet`, `[HttpPost`, `[HttpPut`, `[HttpPatch`, `[HttpDelete`, `[Route`, `MapGet`, `MapPost`, `MapPut`, `MapPatch`, `MapDelete`, `HttpTrigger`, `app.get`, `router.get`, `@app.get`, `@router.get`, `@GetMapping`, `@PostMapping`, or similar route declarations.

For .NET repositories, do not stop after reading `Program.cs`. If `Program.cs` maps `/`, `/health`, Swagger, or diagnostics routes, continue scanning feature folders and controller folders under `scanPath`.

Ignore:

- `.git/`
- `.github/`
- `bin/`
- `obj/`
- `packages/`
- `node_modules/`
- `dist/`
- `build/`
- `.vs/`
- `.vscode/`
- test projects and test files
- generated code
- documentation-only folders

Discover API endpoints from source code and API metadata files. Supported discovery signals include, but are not limited to:

- ASP.NET Core controllers and route attributes.
- Minimal API route registrations.
- Azure Functions HTTP triggers.
- Existing OpenAPI/Swagger documents.
- Express, Fastify, NestJS, Flask, FastAPI, Django REST Framework, Spring Boot, JAX-RS, or similar route definitions when present.

Do not stop after finding the first API, first controller, first folder, or first endpoint. Continue scanning until all relevant files under `scanPath` have been considered.

Ignore infrastructure-only endpoints such as health checks, root redirects, Swagger UI, metrics, readiness, liveness, and diagnostics unless they are the only endpoints in the repository. Do not return a spec that contains only infrastructure endpoints when application endpoints exist.

If the only paths you are about to return are `/`, `/health`, `/swagger`, `/metrics`, `/ready`, `/live`, or other infrastructure paths, stop and continue scanning the repository file inventory. Return those infrastructure-only paths only after confirming no application route files or application endpoints exist anywhere under `scanPath`.

For ASP.NET Core controller files, read every controller file discovered under `scanPath`; extract every method with HTTP route attributes; combine class-level and method-level routes; and include every resulting endpoint.

---

# Grouping Rules

Group endpoints into specs by the most natural API/domain/service boundary visible in the repository.

Use these signals, in order:

1. Existing OpenAPI/Swagger document boundaries.
2. Project/service folders.
3. API area/domain folders.
4. Controller/module/router/function group.
5. A single repository-level API only when no clearer boundary exists.

Each discovered application endpoint must appear in exactly one returned OpenAPI spec.

When multiple APIs/domains/services are discovered, return multiple `specs` entries.

Do not collapse unrelated APIs into one generic spec when clear boundaries exist.

Coverage is more important than schema detail. If response space is limited, return minimal valid OpenAPI specs for all discovered APIs/endpoints rather than a detailed spec for only one API.

---

# OpenAPI Requirements

Every `open-api` object must:

- Use `"openapi": "3.1.0"`.
- Include `info.title`.
- Include `info.version`, defaulting to `"3.1.0"` when the source does not expose an API version.
- Include a `paths` object.
- Include every discovered endpoint for that API/domain/service.
- Include `components.securitySchemes` as an object.
- Include `components.schemas` as an object.
- Include `security` as an array. Use an empty array when no security is detected.

For each endpoint, include where inferable:

- path
- HTTP method
- operationId
- summary
- parameters
- requestBody
- responses
- response schemas
- authentication/security

When details are uncertain, prefer conservative valid OpenAPI over invented specifics. Include the path and method with a basic response description rather than omitting the endpoint.

---

# Field Rules

For each `specs` item:

- `domain-api`: lowercase kebab-case identifier for the API/domain/service.
- `open-api`: complete OpenAPI 3.1 JSON object, not a string.
- `serviceName`: human-readable API/service name.
- `sourcePath`: repository path, folder, file, or project most responsible for the spec.
- `fileName`: lowercase kebab-case `.json` filename.
- `contentType`: exactly `"application/json"`.

No additional top-level properties are allowed.

No additional properties are allowed inside each `specs` item.

---

# Final Check

Before returning:

- Verify the response is valid JSON.
- Verify the top-level object contains only `specs`.
- Verify each spec item has exactly the required fields.
- Verify each `open-api` object has `openapi`, `info`, `paths`, `components`, and `security`.
- Verify all discovered application endpoints are represented.
- Verify the response is not health-only or root-redirect-only when application route files exist under `scanPath`.
- Verify the response contains no markdown or prose.
