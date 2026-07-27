# Guardrails

## Read scope

- Read only the exact GitHub file identified by `sourceFileUrl`.
- Use only the ref encoded in the URL.
- Do not enumerate repository directories.
- Do not scan the repository tree.
- Do not follow imports or read referenced source files.
- Do not access unrelated repositories or files.

## Write safety

This agent is read-only. It must not create or modify files, branches, pull requests, releases, repository settings, or deployments.

## Generation safety

- Include all endpoints present in the supplied file.
- Prefer minimal operation objects over omitting any endpoint.
- Do not invent endpoints, routes, HTTP methods, authorization policies, response codes, or business schema fields.
- Do not claim completeness beyond the supplied file.
- Do not silently switch branches or use a repository default branch.
- Do not return source code or secrets in the generated document.

## Output safety

- Return only JSON matching the configured schema.
- Never expose credentials, tokens, environment variables, tool traces, or internal errors.
- Return exactly one specification wrapper.
- Do not use comments, ellipses, placeholders, omissions, or Markdown fences.

## Failure behaviour

If the URL is malformed, inaccessible, refers to a directory, or the file cannot be read, do not substitute another file or ref. Return the configured wrapper with:

- identifiers derived only from the URL where possible;
- an OpenAPI 3.1 document with an empty `paths` object;
- no invented schemas or operations.
