# Database Schema Source Discovery

This project was built with the microsoft-foundry skill. Before working on or answering questions about foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/dbschema-source-discovery/`.
- Preserve the exact one-property `sourceUrl` input contract.
- Return only deterministic, credential-free GitHub blob URLs from the input repository and ref.
- Select database sources without using an LLM and report files excluded by safety limits.
- Run unit tests before deployment.
