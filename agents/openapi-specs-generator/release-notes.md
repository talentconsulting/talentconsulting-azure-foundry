# Release Notes

## 1.1.0

### Changed

- Reframed `scanPath` as the inclusive base path for one exhaustive repository-tree scan.
- Added a first-principles discovery workflow: resolve boundary, inventory candidates, reconstruct routes, form specs, and verify completeness.
- Added framework-agnostic discovery for controllers, routers, minimal APIs, serverless triggers, mounted prefixes, existing specifications, and supporting models.
- Required one generator invocation per repository/base path rather than treating per-controller invocation as the discovery mechanism.
- Strengthened completeness, evidence, scan-boundary, and partial-result guardrails.

### Notes

The generator must finish discovery across the full code tree below the supplied base path before returning specifications. It remains read-only and retains the existing input and output schema.

## 1.0.0

### Added

- Repository and scan path inputs.
- Full recursive scan behavior for API endpoints under `scanPath`.
- OpenAPI 3.1 JSON output.
- `specs` array wrapper for multiple API/domain/service specs.
- Read-only GitHub access.

### Notes

This agent generates OpenAPI JSON objects and returns them in the configured response schema. It does not write files, create branches, or open pull requests.
