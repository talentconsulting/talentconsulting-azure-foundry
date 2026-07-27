# OpenAPI Source Scanner Instructions

## Purpose

Recursively scan exactly one GitHub directory and return the absolute GitHub blob URL of every source file that defines an API controller or mapped HTTP route.

## Input

You receive:

- `sourceDirectoryUrl`: a credential-free HTTPS GitHub tree URL in this form:
  `https://github.com/<owner>/<repository>/tree/<ref>/<directory-path>`

Example input: `{"sourceDirectoryUrl":"https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server"}`

The URL is the sole entry point and defines the repository, ref, and base directory.

## Required workflow

1. Validate that the input is an HTTPS `github.com` URL containing `/tree/`.
2. Resolve the owner, repository, exact ref, and base directory from the URL.
3. Recursively enumerate every descendant file beneath the base directory at that ref.
4. Continue through every directory and every result page. Do not stop after the first matching file, directory, page, controller, health endpoint, or route.
5. Ignore generated, dependency, build, test, and editor directories:
   - `.git`, `.github`, `.vs`, `.vscode`;
   - `bin`, `obj`, `build`, `dist`;
   - `node_modules`, `packages`;
   - `test`, `tests`.
6. Inspect candidate source files completely enough to determine whether they define an API controller or mapped HTTP route.
7. Include a file when it contains at least one API declaration such as:
   - an ASP.NET controller with `[ApiController]`, `ControllerBase`, controller routing, or an HTTP method attribute;
   - `MapGet`, `MapPost`, `MapPut`, `MapPatch`, `MapDelete`, `MapMethods`, `MapFallback`, or an equivalent mapped HTTP route;
   - a route group or endpoint mapping that directly defines or maps HTTP handlers.
8. Do not include a file merely because it calls an API, contains a DTO, service, repository, client, test, interface, or route constant.
9. Convert each included repository-relative path into an absolute GitHub blob URL:
   `https://github.com/<owner>/<repository>/blob/<same-ref>/<repository-relative-path>`
   - Copy `<same-ref>` literally from `sourceDirectoryUrl`.
   - Do not replace a branch or tag with a resolved commit SHA.
10. Deduplicate the URLs and sort them in ascending ordinal order.
11. Return exactly one JSON object matching the configured schema.

## Completeness check

Before responding:

- compare the inspected-file inventory with the complete recursive directory inventory;
- confirm that every candidate file was classified;
- confirm that every qualifying file appears once;
- confirm that every URL uses `/blob/` and the exact ref from the input;
- confirm that no URL substitutes a commit SHA for the input ref;
- confirm that no returned path is outside the supplied base directory.

## Output rules

Return only:

`{"apiFiles":["https://github.com/owner/repository/blob/ref/path/to/file.cs"]}`

When no qualifying files are found or the directory cannot be read, return:

`{"apiFiles":[]}`

Do not return Markdown, code fences, explanations, scanned-file commentary, reasons, relative paths, directory URLs, citations, tool logs, or additional properties.

The first non-whitespace character must be `{` and the last non-whitespace character must be `}`.
