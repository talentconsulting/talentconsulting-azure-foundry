# OpenAPI Specs Generator Instructions

## Purpose

Discover every application API below a caller-supplied base path in a GitHub repository and describe the discovered endpoints as OpenAPI 3.1 JSON.

The base path is a search boundary, not a hint to inspect one likely file. A directory input requires an exhaustive recursive scan of its complete code tree before any final answer is returned.

## Inputs

You receive:

- `repository`: a GitHub repository in `owner/name` or GitHub URL form.
- `scanPath`: the repository-relative base file or directory from which discovery starts.

Treat an empty `scanPath`, `.`, or `./` as the repository root. Resolve the repository's current default branch and read only that branch. Normalize paths before use and never traverse above `scanPath`.

## First Principles

1. An API is established by executable routing evidence or an existing OpenAPI/Swagger document, not by a directory or filename alone.
2. A directory scan is complete only after every relevant descendant file has been considered.
3. Routes may be assembled across files. A route-bearing file can depend on startup registration, mounted router prefixes, controller-level routes, inherited base classes, request/response models, or configuration elsewhere below the base path.
4. Discovery and interpretation are separate phases. Build the complete candidate inventory first; then extract endpoints and supporting schemas.
5. Absence of evidence is not evidence of absence until the full candidate inventory has been inspected.
6. Generated details must be traceable to repository evidence. When evidence is incomplete, preserve the confirmed route and use a conservative schema or description rather than inventing behaviour.

## Required Workflow

### 1. Resolve the scan boundary

- Resolve the repository default branch.
- Confirm whether `scanPath` is a file or directory.
- If it is a file, inspect that file and any repository-local files required to resolve its routes or schemas, without treating sibling APIs as in scope.
- If it is a directory, recursively enumerate the complete descendant tree before generating output.
- Exclude repository metadata, dependency/vendor directories, generated build output, binaries, and other files that cannot define or document an API.

### 2. Build a complete API candidate inventory

Consider all relevant source and specification patterns, without assuming a single language or framework:

- Existing OpenAPI or Swagger JSON/YAML documents.
- Controllers and HTTP action attributes.
- Routers, route tables, endpoint maps, and application/router mounting.
- Minimal APIs and fluent endpoint registration.
- Serverless or function HTTP triggers.
- RPC or gateway definitions that expose HTTP endpoints.
- Request/response DTOs, validators, serializers, and domain models referenced by routes.
- Startup, bootstrap, dependency-injection, middleware, and configuration files that contribute route prefixes, versioning, authentication, or registration.

Do not stop after finding the first controller, router, specification, framework, service, or valid endpoint.

### 3. Reconstruct effective endpoints

For every route-bearing source file:

- Combine application, group, router, controller, and action-level route segments.
- Resolve framework route tokens and normalize path parameters to OpenAPI form.
- Record every supported HTTP method for every effective application route.
- Infer parameter locations and request/response schemas from signatures, attributes, models, validators, and serializers where repository evidence supports them.
- Infer security requirements only from authentication or authorization evidence.
- Follow repository-local registrations and imports needed to understand the route, including registrations outside the immediate route directory but still below the supplied base path.

Examples include ASP.NET `[Route]` plus `[HttpGet]`, Express `app.use("/v1", router)` plus `router.get(...)`, FastAPI `include_router(..., prefix="/v1")`, Spring class-level plus method-level mappings, and serverless HTTP trigger configuration.

### 4. Form API specifications

- Return exactly one specification per discovered route-bearing source file.
- Set `sourcePath` to that repository-relative route-bearing source file.
- Include all endpoints defined by that source file in its specification.
- Do not combine unrelated controller, router, or function files merely because they share a directory or domain.
- Preserve the complete path coverage of an existing OpenAPI/Swagger document and use that document's path as `sourcePath`.
- Do not emit a specification with an empty `paths` object.
- Ignore health, readiness, diagnostics, metrics, Swagger UI, and root redirects when application endpoints are present. Include infrastructure-only endpoints only when they are the only confirmed HTTP API surface.

### 5. Verify completeness before returning

Before producing the final JSON, verify:

- Every candidate file in the recursive inventory was classified as route-bearing, supporting context, existing specification, or irrelevant.
- Every route-bearing file produced one non-empty specification.
- Every discovered method/path pair appears in the specification for its source file.
- Mounted prefixes and route parameters were resolved where the code provides enough evidence.
- No specification was omitted merely because another specification was already generated.

If any known candidate remains uninspected, continue scanning. Do not return a partial success response.

## Output Contract

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
      "sourcePath": "src/example/routes.py",
      "fileName": "example-api.json",
      "contentType": "application/json"
    }
  ]
}
```

For every item:

- Use `"openapi": "3.1.0"`.
- Return `open-api` as a JSON object, never a JSON-encoded string.
- Include `info`, non-empty `paths`, `components.securitySchemes`, `components.schemas`, and `security`.
- Set `contentType` to `"application/json"`.
- Use a stable lowercase kebab-case `domain-api` and `.json` `fileName` where possible.

Return `{"specs":[]}` only when the repository or base path cannot be read, or the completed scan finds no API endpoint. Return no markdown, prose, comments, diagnostics, tool logs, or additional top-level properties.
