# Single-File OpenAPI Generator Instructions

## Purpose

Generate exactly one complete OpenAPI 3.1 JSON specification from one API source file stored in GitHub, using the source files that define its request and response payload types as supporting context.

## Input

You receive:

- `sourceFileUrl`: a full, credential-free GitHub file URL in this form:
  `https://github.com/<owner>/<repository>/blob/<branch-or-ref>/<path-to-file>`
- `payloadFiles`: an object whose keys are repository-relative source paths and whose values are arrays of relevant DTO type names. These files were deterministically discovered from the controller's request and response signatures.

Example input: `{"sourceFileUrl":"https://github.com/talentconsulting/talentsuite-bidmanager/blob/main/src/TalentSuite.Server/Bids/Controllers/BidsController.cs","payloadFiles":{"src/TalentSuite.Server/Bids/Contracts/CreateBidRequest.cs":["CreateBidRequest"],"src/TalentSuite.Server/Bids/Contracts/BidResponse.cs":["BidResponse"]}}`

The URL defines the repository, ref, controller path, and ref to use for every supplied payload path.

## Required workflow

1. Validate that `sourceFileUrl` is an HTTPS `github.com` file URL containing `/blob/`.
2. Parse the owner, repository, ref, and complete file path from the URL.
3. Use the GitHub tool to read that exact file at that exact ref.
4. Validate every `payloadFiles` key as a clean repository-relative path and read that exact path from the same repository and exact ref as `sourceFileUrl`.
5. Do not read another branch, tag, or commit.
6. Do not search for additional files or read sibling controllers. Treat `payloadFiles` as the complete supporting-file inventory produced by the scanner.
7. Inspect the complete controller and discovered payload source files before generating the specification.
8. Identify every route-bearing operation declared in the file:
   - controller or class route prefixes;
   - HTTP method attributes or equivalent route declarations;
   - method-level route templates;
   - route parameters and constraints;
   - query, header, and body inputs visible in the source;
   - response types and status codes visible in the source;
   - authentication or authorization requirements visible in the source.
9. Create an internal endpoint ledger containing every discovered HTTP method, normalized path, and source method name.
10. Create an internal payload-source ledger from `payloadFiles`, confirming that each listed DTO type is declared in its mapped file.
11. Build one OpenAPI 3.1 document containing every endpoint ledger entry and the schemas supported by the payload-source ledger. Never stop after the first endpoint.
12. Before returning, compare `openapi.paths` with the endpoint ledger and add any missing method/path; compare referenced component schemas with the payload-source ledger and add any missing payload schema.
13. Return exactly one JSON object matching the configured output schema.

## OpenAPI rules

The `openapi` object must:

- use `openapi: "3.1.0"`;
- include `info`, `paths`, `components`, and `security`;
- include every HTTP method and normalized path declared in the source file;
- use stable, unique `operationId` values based on source method names when available;
- make every path parameter required;
- include request bodies only when supported by the source;
- include response codes and schemas only when supported by the source;
- define referenced schemas under `components.schemas`;
- define visible authentication under `components.securitySchemes`;
- remain internally consistent and valid JSON.

When a referenced type cannot be located at the same repository ref, use the safest minimal schema supported by its usage. Do not invent business fields.

Endpoint completeness has higher priority than descriptions or detailed component schemas. For a large file, keep summaries, responses, and unknown schemas minimal so every endpoint fits in the response.

## Wrapper rules

- `domainApi`: lowercase kebab-case service identifier derived from the controller or API name.
- `serviceName`: human-readable API name derived from the file.
- `sourcePath`: repository-relative path parsed from `sourceFileUrl`.
- `fileName`: `<domainApi>.json`.
- `contentType`: `application/json`.

## Output rules

Return only the configured JSON object.

Do not return:

- Markdown or code fences;
- progress commentary;
- a scanned-files list;
- multiple specifications;
- tool logs or citations;
- explanations before or after the JSON;
- properties not present in the output schema.

Never use:

- JSON comments;
- ellipses;
- placeholder paths;
- `TODO`;
- phrases such as "other operations omitted", "remaining endpoints", or "for brevity";
- prose standing in for paths or schemas.

The response must parse with a standard JSON parser. The first non-whitespace character must be `{` and the last non-whitespace character must be `}`. A Markdown code fence is not valid JSON and is forbidden, even when the interface normally formats JSON as Markdown.

Final check before responding: remove every Markdown fence marker. Emit the JSON object itself.
