# Service Dependency Source Discovery

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/service-dependency-source-discovery/`.
- Preserve the exact one-property `sourceUrl` input contract.
- Return only deterministic, credential-free GitHub blob URLs from the input repository and ref.
- Select only outbound HTTP API and gRPC clients, registrations, and endpoint configuration without using an LLM.
- Never return secret values or download private repositories.
- Run unit tests before deployment.
