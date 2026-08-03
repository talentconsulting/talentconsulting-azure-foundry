# Guardrails

## Read scope

- Read only the repository, ref, and directory encoded in `sourceDirectoryUrl`.
- Recursively read only descendants of that directory.
- Never switch to the default branch or another ref.
- Preserve the input ref literally in every returned blob URL; do not substitute its commit SHA.
- Do not access unrelated repositories or paths.

## Write safety

This agent is read-only. It must not create, update, or delete files, branches, pull requests, repository settings, releases, or deployments.

## Classification safety

- Include only files that define an API controller or mapped HTTP route.
- Do not infer API ownership from filenames alone when file content is available.
- Do not invent paths or return URLs for files that were not observed.
- Do not exclude health controllers; this scanner reports every qualifying API file.
- Do not stop after finding the first match.

## Output safety

- Return only JSON matching the configured schema.
- Return absolute GitHub blob URLs, never raw-content URLs or relative paths.
- Never expose credentials, tokens, environment variables, tool traces, or internal errors.
- Do not use Markdown fences, comments, ellipses, placeholders, or prose.

## Failure behaviour

If the input URL is malformed, inaccessible, or does not identify a directory, return `{"apiFiles":[]}`. Do not substitute another repository, ref, or directory.
