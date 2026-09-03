# .NET Version Source Discovery

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/dotnet-version-source-discovery/`.
- Preserve the exact one-property `sourceUrl` input contract.
- Return only deterministic, credential-free GitHub blob URLs for `.csproj` and `global.json` files under the requested tree.
- Ignore `bin`, `obj`, `packages`, and `node_modules` directories.
- Never download private repositories or return anything but file locations and exclusion reasons.
- Run unit tests before deployment.
