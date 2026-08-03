# OpenAPI Spec Workflow

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/openapi-spec-workflow/`.
- Preserve the discovery and generator agents' root JSON contracts.
- Keep generation concurrency bounded and output ordering deterministic.
- Send all successfully generated specifications to the PR creator in one request.
- Run the unit tests before deployment.
