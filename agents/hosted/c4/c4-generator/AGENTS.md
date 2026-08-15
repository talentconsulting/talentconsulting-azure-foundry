# C4 Generator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/c4-generator/`.
- Accept the public `sourceUrl` and workflow-only `sourceFiles` bundle of validated same-repository blob URLs.
- Return C4 JSON plus draw.io `mxfile` XML, without Markdown or a wrapper.
- Record source evidence, never credentials, tokens, connection strings, or secret values.
- Preserve the repository, ref, path, `c4Model`, and `diagrams` output contract.
- Run unit tests before deployment.
