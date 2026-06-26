# Governance Standard: Source Control For AI Assets

## Standard Statement

All material AI assets must be stored, reviewed, versioned, and released through approved source control repositories.

This includes prompts, agent instructions, workflow definitions, tool contracts, model configuration, evaluation assets, dataset records, risk assessments, and operating documentation.

## Scope

This standard applies to:

- AI agents and copilots.
- Prompt templates and system instructions.
- Retrieval, summarisation, classification, generation, and automation workflows.
- Model deployment configuration.
- Evaluation datasets, scoring rubrics, and test results.
- Tool, connector, and function contracts.
- Safety, compliance, security, and privacy controls.

## Required Repository Evidence

Each production AI asset must have:

- A manifest file identifying ownership, purpose, status, and version.
- A clear change history through commits and pull requests.
- Documented model and tool dependencies.
- Evaluation criteria and evidence for release decisions.
- Data classification and permitted input/output handling.
- Risk assessment and mitigation record.
- Approval evidence before production use.
- Retirement or rollback instructions.

## Pull Request Review Expectations

Reviewers should confirm:

- The business purpose is clear and still valid.
- The change is understandable and scoped.
- Prompt, workflow, or agent behavior has relevant tests.
- New or changed data flows are documented.
- Tool permissions remain least privilege.
- Safety and policy controls are still appropriate.
- Evaluation results meet acceptance criteria.
- Release notes identify operational impact.

## Release Controls

Production AI assets should be released using immutable tags or release records. Runtime systems should reference approved versions rather than mutable draft files.

Recommended status values:

- `draft`: work in progress, not approved for use.
- `review`: ready for formal review.
- `approved`: accepted by required reviewers.
- `released`: deployed or referenced by a production system.
- `retired`: no longer used.

## Exceptions

Exceptions should be time-bound, risk-assessed, and approved by the accountable governance owner. Exception records should be stored in `risks/exceptions/`.

