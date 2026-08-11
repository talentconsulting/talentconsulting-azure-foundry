# Service Dependency Generator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/service-dependency-generator/`.
- Accept the public `sourceUrl` and workflow-only `sourceFiles` bundle of validated same-repository blob URLs.
- Return the service-dependency catalog itself as JSON, without Markdown or a wrapper.
- Record configuration keys and source evidence, never credentials, tokens, connection strings, or secret values.
- Preserve the repository, ref, path, and dependencies output contract.
- Run unit tests before deployment.
