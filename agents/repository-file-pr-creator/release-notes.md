# Release Notes

## 1.0.0

- Initial source-controlled agent definition.
- Accepts structured file changes containing `filename`, `content`, `repository`, and `path`.
- Creates a branch, writes requested files, and opens a pull request.
- Adds guardrails for repository scope, path validation, branch-only writes, and pull request safety.
