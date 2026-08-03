# Release Notes

## 1.0.0

- Created the read-only `openapi-spec-scanner` prompt agent.
- Accepts one GitHub tree URL containing the repository, ref, and base directory.
- Recursively detects API controllers and mapped HTTP routes.
- Returns a sorted, deduplicated JSON list of absolute GitHub blob URLs.
- Preserves the exact branch, tag, or ref supplied in the input URL.
