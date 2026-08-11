# Event and Command Catalog Workflow

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/eventcatalog-workflow/`.
- Invoke deterministic source discovery before generation and pass only its validated file bundle to the generator.
- In deferred mode, return the complete catalog without invoking the PR creator.
- In direct mode, publish through `eventcatalog-pr-creator` and never write to GitHub directly.
- Fail the workflow if any generator batch fails or the merged catalog is empty; never publish partial output.
- Run the unit tests before deployment.
