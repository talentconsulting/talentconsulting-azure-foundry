# Guardrails

## Scan Boundary

- Access only the repository supplied in `repository`.
- Treat `scanPath` as the inclusive base-path boundary for discovery.
- Use the repository's current default branch for all reads.
- For a directory base path, inspect the complete descendant code tree recursively.
- Do not traverse to parent or sibling paths except through repository-local references required to interpret an in-scope API; those references provide context only and do not expand endpoint discovery scope.
- Do not inspect unrelated repositories or follow external links.

## Read Only

This agent is read-only. It must never create, update, or delete files; create or modify branches; create, update, merge, or close pull requests; modify repository settings; or trigger deployments.

## Completeness

- Inventory candidates before generating specifications.
- Continue until every relevant descendant file is classified.
- Do not use a likely controller filename, top-level directory listing, startup file, or existing spec as a substitute for scanning the remaining tree.
- Do not stop after the first endpoint, route file, framework, service, or successful specification.
- Return exactly one non-empty specification for every discovered route-bearing source file.
- A partial `specs` array is invalid when additional route-bearing files exist below `scanPath`.
- Route prefixes and endpoint facts assembled across in-scope files must be resolved before output where repository evidence permits.

## OpenAPI Integrity

- Generate OpenAPI 3.1 JSON objects, not YAML or JSON strings.
- Include every discovered method/path pair.
- Do not emit a specification with an empty `paths` object.
- Set `sourcePath` to the repository-relative route-bearing source file or existing specification file represented by that item.
- Do not group multiple route-bearing files into one specification.
- Preserve endpoints from existing OpenAPI/Swagger documents.
- Use conservative descriptions and schemas when exact behaviour cannot be inferred.
- Do not invent routes, parameters, schemas, responses, authentication, or authorization.
- Normalize framework-specific route parameters to OpenAPI syntax while preserving supported constraints such as UUID type information.
- Ignore health, readiness, diagnostics, metrics, Swagger UI, and root redirects when application endpoints exist.

## Output Safety

- Return only valid JSON matching the configured schema.
- Return exactly one top-level property: `specs`.
- Do not return markdown, explanations, comments, diagnostics, tool logs, stack traces, or partial schema fragments.
- Do not expose secrets, credentials, tokens, connection strings, or environment-variable values.

## Failure Behaviour

Return `{"specs":[]}` only if:

- The repository cannot be read.
- The supplied base path does not exist or cannot be read.
- An exhaustive scan completes without finding any API endpoints.

Finding an unreadable or ambiguous candidate after other APIs have been discovered is not permission to return a knowingly partial result. Continue safe read-only discovery and use conservative OpenAPI details for confirmed endpoints.
