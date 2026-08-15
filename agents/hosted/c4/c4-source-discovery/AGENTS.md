# C4 Source Discovery

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/c4-source-discovery/`.
- Preserve the exact one-property `sourceUrl` input contract.
- Return only deterministic, credential-free GitHub blob URLs from the input repository and ref.
- Select architecture evidence for C4 context and container diagrams without using an LLM.
- Never return secret values or download private repositories.
- Run unit tests before deployment.
