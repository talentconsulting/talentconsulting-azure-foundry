# Local Dev Config Generator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/local-dev-config-generator/`.
- Accept the `sourceUrl` and `sourceFiles` contract; both are required, and `sourceFiles` entries must be validated same-repository, same-ref GitHub blob URLs.
- Return the local-dev-config catalog itself as JSON, without Markdown or a wrapper.
- Record configuration key names and source evidence but never return secret values -- no credentials, tokens, connection-string values, or literal endpoint hostnames or URLs.
- Preserve the repository, ref, path, localServices, and configurationKeys output contract.
- Run unit tests before deployment.
