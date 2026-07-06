# Release Notes

## 1.0.0

### Added

- Initial OpenAPI Spec Generator agent definition.
- Configurable repository input.
- Configurable scan path input.
- Structured JSON output containing YAML content.
- GitHub MCP tool configuration.
- Read-only guardrails.
- Evaluation scenarios for empty, GET, POST, and authenticated APIs.

### Notes

This agent generates an OpenAPI YAML document but does not write the file back to the repository. A downstream workflow step should save the `open-api` value to the file path required by the pipeline.
