# Local Dev Config Source Discovery

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/local-dev-config-source-discovery/`.
- Preserve the exact one-property `sourceUrl` input contract.
- Return only deterministic, credential-free GitHub blob URLs from the input repository and ref.
- Select Docker Compose files, recognised application-config filenames, and `.env.example`-style files on filename alone; only fall back to cache/database/message-broker/object-storage client registration evidence in source code when no Docker Compose file is present in the tree.
- Never return secret values, environment variable values, or download private repositories -- only file locations and exclusion reasons.
- Run unit tests before deployment.
