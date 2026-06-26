# AI Source Control Template

This repository is a template for storing AI workflows, agents, prompts, evaluations, model configuration, risk records, and governance evidence in source control.

Use it as the canonical implementation pattern linked from AI governance standards, delivery playbooks, and assurance documentation.

## Purpose

AI systems change through prompts, orchestration logic, model choices, tools, datasets, policies, and evaluation criteria. Those changes should be reviewed, versioned, tested, and auditable in the same way as application code.

This template helps teams:

- Keep AI assets discoverable and owned.
- Review changes before release.
- Preserve evidence for governance, audit, and operational support.
- Separate reusable prompts, agents, workflows, and evaluations.
- Track model, data, tool, and policy dependencies.

## Repository Layout

```text
.
├── agents/                 # Agent definitions, tool access, instructions, guardrails
├── workflows/              # AI workflow designs and orchestration specs
├── prompts/                # Reusable prompt templates and prompt change history
├── evaluations/            # Test sets, scoring criteria, evaluation runs
├── datasets/               # Dataset cards and small sample datasets
├── models/                 # Model cards, deployment settings, model selection records
├── tools/                  # Tool and connector contracts exposed to agents/workflows
├── policies/               # Safety, privacy, security, and usage policies
├── risks/                  # AI risk assessments and mitigations
├── decisions/              # Architecture and governance decision records
├── docs/                   # Standards-facing documentation and operating model
├── examples/               # Worked examples teams can copy from
└── schemas/                # Lightweight metadata schemas for repository assets
```

## Minimum Standard For Any AI Asset

Every committed AI asset should include:

- Owner and accountable team.
- Business purpose and user group.
- Version and change summary.
- Model or service dependency.
- Data inputs and data classification.
- Tool access and permissions.
- Evaluation approach and acceptance criteria.
- Known risks, mitigations, and escalation path.
- Release status: `draft`, `review`, `approved`, `released`, or `retired`.

## Recommended Change Flow

1. Create or update the asset in the relevant folder.
2. Update metadata, evaluation criteria, and risk notes.
3. Run the relevant evaluations or document why they are not required.
4. Raise a pull request with the governance checklist completed.
5. Obtain review from engineering, product owner, and risk/compliance where required.
6. Tag or release approved versions used in production.

## Quick Start

Copy one of the examples:

- [Example support triage agent](examples/support-triage-agent/)
- [Example document summarisation workflow](examples/document-summarisation-workflow/)

Then complete:

- [Agent manifest template](templates/agent-manifest.yaml)
- [Workflow manifest template](templates/workflow-manifest.yaml)
- [Prompt template](templates/prompt-template.md)
- [Evaluation plan template](templates/evaluation-plan.md)
- [Risk assessment template](templates/risk-assessment.md)

## Governance Linkage

This repository is designed to support governance standards covering:

- AI asset inventory.
- Prompt and agent change management.
- Human oversight.
- Model and dataset traceability.
- Evaluation and acceptance evidence.
- Safety, privacy, and security controls.
- Operational monitoring and retirement.

See [docs/governance-source-control-standard.md](docs/governance-source-control-standard.md) for suggested wording to link from your standards documentation.

For a stable standards link target, use [docs/repository-index.md](docs/repository-index.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the recommended branch, review, versioning, release, and retirement process.
