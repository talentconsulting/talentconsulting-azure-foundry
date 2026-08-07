# Database Schema Generator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/dbschema-generator/`.
- Accept the public `sourceUrl` contract and the workflow-only `sourceFiles` bundle of validated same-repository blob URLs.
- Return the database representation itself as JSON, without Markdown or a wrapper.
- Keep source access restricted to credential-free GitHub tree URLs.
- Preserve the tables, columns, relationships, indexes, and types output contract.
- Run the unit tests before deployment.
