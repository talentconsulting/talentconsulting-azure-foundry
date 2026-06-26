# AI Asset Operating Model

## Roles

| Role | Responsibilities |
| --- | --- |
| Asset owner | Business accountability, approval, fitness for purpose |
| Engineering owner | Implementation, versioning, release, rollback |
| Risk/compliance reviewer | Policy alignment, risk acceptance, audit evidence |
| Data owner | Data classification, usage permission, retention |
| Operations owner | Monitoring, incidents, support, retirement |

## Lifecycle

1. Discover and classify the AI use case.
2. Create an asset manifest and risk assessment.
3. Implement prompts, agents, workflows, tools, and configuration.
4. Define evaluations and acceptance thresholds.
5. Review through pull request.
6. Release using an approved version.
7. Monitor behavior and incidents.
8. Reassess after material changes.
9. Retire or archive when no longer needed.

## Material Change Examples

A change is usually material when it:

- Changes system instructions, guardrails, or refusal behavior.
- Changes model family, model version, or deployment region.
- Adds, removes, or expands tool permissions.
- Changes data sources, retrieval indexes, or data classification.
- Changes evaluation acceptance thresholds.
- Expands the user population or business process scope.

