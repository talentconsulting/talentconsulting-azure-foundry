# C4 Workflow

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/c4-workflow/`.
- Invoke deterministic source discovery before generation and pass only its validated file bundle to the generator.
- In deferred mode, return the complete C4 output without invoking the PR creator.
- In direct mode, publish through `c4-pr-creator` and never write to GitHub directly.
- Generate from the complete discovered bundle once; C4 diagrams should not be merged from partial batches.
- Run unit tests before deployment.
