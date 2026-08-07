# Database Schema Workflow

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/dbschema-workflow/`.
- Invoke deterministic source discovery before generation and pass only its validated file bundle to the generator.
- In deferred mode, return the complete schema without invoking the PR creator.
- In direct mode, publish through `dbschema-pr-creator` and never write to GitHub directly.
- Run the unit tests before deployment.
