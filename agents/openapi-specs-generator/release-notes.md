# Release Notes

## 1.0.0

### Added

- Repository and scan path inputs.
- Full recursive scan behavior for API endpoints under `scanPath`.
- OpenAPI 3.1 JSON output.
- `specs` array wrapper for multiple API/domain/service specs.
- Read-only GitHub access.

### Notes

This agent generates OpenAPI JSON objects and returns them in the configured response schema. It does not write files, create branches, or open pull requests.
