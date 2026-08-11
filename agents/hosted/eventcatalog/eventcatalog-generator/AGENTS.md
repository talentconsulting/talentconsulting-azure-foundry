# Event and Command Catalog Generator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/eventcatalog-generator/`.
- Accept the public `sourceUrl` contract and the workflow-only `sourceFiles` bundle of validated same-repository blob URLs.
- Return the event and command catalog itself as JSON, without Markdown or a wrapper.
- Keep source access restricted to credential-free GitHub tree URLs.
- Preserve the repository, ref, path, commands, and events output contract.
- Run the unit tests before deployment.
