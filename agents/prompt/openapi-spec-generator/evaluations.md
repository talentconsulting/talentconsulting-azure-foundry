# Evaluations

## Evaluation 1: One controller with multiple endpoints

Given a GitHub blob URL for one controller containing several HTTP method attributes, the response must contain one wrapper and every declared method/path combination.

Acceptance checks:

- exactly one JSON object is returned;
- `sourcePath` equals the path encoded in the URL;
- every endpoint in the file exists under `openapi.paths`;
- no sibling controller endpoints are present;
- no commentary surrounds the JSON.

## Evaluation 2: Branch fidelity

Given a URL containing `/blob/feature/test-api/`, the agent must read that ref and must not read the default branch.

## Evaluation 3: Single-file boundary

Given a controller that references DTOs in other files, the agent must not fetch those files or invent their business fields.

## Evaluation 4: Invalid URL

Given a repository tree URL or a URL without `/blob/`, the agent must not scan the repository. It returns one schema-valid wrapper with an empty `paths` object.

## Evaluation 5: Route completeness

Given a controller containing class-level routing, method-level routing, route constraints, and multiple HTTP verbs, the generated OpenAPI document must normalize and include every combination.

## Evaluation checks

- Output is valid JSON and matches the manifest schema.
- `openapi.openapi` is `3.1.0`.
- The result contains exactly one specification.
- The agent reads exactly one GitHub file.
- The result contains no Markdown, commentary, citations, or tool logs.
