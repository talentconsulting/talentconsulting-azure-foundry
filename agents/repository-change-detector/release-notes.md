# Release Notes

## 1.0.0

### Added

- Initial Repository Change Detector agent definition.
- Configurable manifest repository input.
- Configurable manifest path input.
- Structured JSON output for workflow `foreach` usage.
- GitHub MCP tool configuration.
- Read-only guardrails.
- Evaluation scenarios for matching, missing, changed, and inaccessible repositories.

### Notes

This agent only identifies repositories that need downstream processing. It does not update the manifest, generate documentation, create pull requests, or write to GitHub.
