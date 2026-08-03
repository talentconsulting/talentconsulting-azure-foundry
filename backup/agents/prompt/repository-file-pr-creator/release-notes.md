# Release Notes

## 1.1.0

- Updated OpenAPI workflow input handling to consume the generator's `openapi` property.

## 1.0.0

- Initial source-controlled agent definition.
- Accepts structured file changes containing `filename`, `content`, `repository`, and `path`.
- Creates a branch, writes requested files, and opens a pull request.
- Adds guardrails for repository scope, path validation, branch-only writes, and pull request safety.
