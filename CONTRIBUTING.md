# Contributing AI Assets

Use this guide when adding or changing AI assets in this repository.

## Branching

Create a short-lived branch for each material change.

Recommended branch names:

- `agent/support-triage-v1`
- `workflow/document-summary-controls`
- `prompt/customer-response-update`
- `eval/add-safety-test-cases`

## Required Files

For a new asset, include:

- Manifest file.
- Prompt, instructions, workflow, or tool contract.
- Evaluation plan.
- Risk assessment.
- Release and rollback notes.

For a material change, update:

- Manifest version and status.
- Relevant evaluation plan or results.
- Risk assessment if behavior, data, model, or tool access changes.
- Release notes.

## Review

Pull requests should be reviewed by the engineering owner and asset owner. Risk, compliance, security, or data-owner review is required when the change affects regulated data, high-impact decisions, external users, security controls, or production tool permissions.

## Versioning

Use semantic versioning where practical:

- Patch version for wording, metadata, or test-only changes.
- Minor version for behavior changes within the approved purpose.
- Major version for purpose, user population, model family, data classification, or tool-permission changes.

## Release

Only `approved` or `released` assets should be referenced by production systems.

Use tags or release records for production versions. Runtime configuration should reference immutable approved versions rather than draft branch content.

## Retirement

When an asset is no longer used:

- Set status to `retired`.
- Record the retirement date and owner.
- Keep historical evaluation and risk evidence.
- Remove production references.

