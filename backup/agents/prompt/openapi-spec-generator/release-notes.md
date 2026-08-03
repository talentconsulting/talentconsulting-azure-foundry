# Release Notes

## 2.2.0

- Accepts the authoritative `payloadFiles` path-to-DTO mapping from `talent-openapi-file-scan`.
- Reads only the supplied payload paths at the controller's exact repository ref.

## 2.1.0

- Added same-ref discovery of source files defining direct and nested request and response payload types.
- Payload source files are supporting schema context and do not create standalone API specifications.

## 2.0.0

- Restored `openapi-spec-generator` as a single-file prompt agent.
- Replaced recursive tree scanning with one required `sourceFileUrl` GitHub blob URL.
- Restricted GitHub access to the exact file and ref encoded in the input.
- Returns exactly one OpenAPI 3.1 specification wrapper.
- Preserves JSON-only structured output and complete endpoint enumeration within the supplied file.
- Rejects abbreviated output, placeholders, comments, ellipses, and omitted endpoints.
- Uses conventional `domainApi` and `openapi` JSON property names for reliable structured output.
