# System Summary Generator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/system-summary-generator/`.
- Accept only already-published catalog data (`database`, `events`, `dependencies`, `apiControllers`) for one repository; never fetch or scan source code directly.
- Return the system summary itself as JSON, without Markdown or a wrapper.
- Ground every field in supplied evidence; never invent capabilities, integrations, or business context.
- Preserve the repository, name, description, domain, capabilities, and confidence output contract.
- Run unit tests before deployment.
