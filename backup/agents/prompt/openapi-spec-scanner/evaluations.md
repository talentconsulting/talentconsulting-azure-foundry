# Evaluations

## Evaluation 1: Multiple controllers

Given a directory containing several ASP.NET controllers, `apiFiles` contains the absolute blob URL for every controller file, sorted and without duplicates.

## Evaluation 2: Minimal API routes

Given a directory containing `Program.cs` with `MapGet`, `MapPost`, and a route group, the `Program.cs` blob URL appears exactly once.

## Evaluation 3: Mixed source tree

DTOs, services, clients, tests, generated files, and route constants without handlers are excluded. Controllers and files with mapped HTTP handlers are included.

## Evaluation 4: Branch fidelity

Given a tree URL for a non-default ref, every returned blob URL uses that same ref. The agent does not read or return files from the default branch.

## Evaluation 5: Recursive completeness

Given qualifying API files in several nested directories and result pages, all qualifying URLs are returned. Discovery does not stop after the first match.

## Evaluation 6: Empty or invalid input

An empty directory, inaccessible directory, blob URL, or malformed URL returns `{"apiFiles":[]}`.

## Acceptance checks

- Output parses as JSON.
- The only top-level property is `apiFiles`.
- Every item is an absolute `https://github.com/.../blob/...` URL.
- URLs are unique and sorted.
- Every qualifying file beneath the supplied directory is represented.
- No file outside the supplied directory or ref is represented.
- No Markdown, commentary, citations, or tool logs surround the JSON.
