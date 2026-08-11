# Service Dependency Workflow

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/service-dependency-workflow/`.
- Invoke deterministic source discovery before generation and pass only its validated file bundle to the generator.
- In deferred mode, return the complete catalog without invoking the PR creator.
- In direct mode, publish through `service-dependency-pr-creator` and never write to GitHub directly.
- Fail if any generator batch fails or the merged dependency catalog is empty; never publish partial output.
- Run unit tests before deployment.
