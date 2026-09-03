# .NET Version Generator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/dotnet-version-generator/`.
- This agent is deterministic -- no model call, no `AZURE_AI_MODEL_DEPLOYMENT_NAME`. Do not introduce one; parsing `.csproj`/`global.json` needs no reasoning.
- Only accept `sourceFiles` that belong to the same repository and ref as `sourceUrl`.
- A `.csproj` with no recognizable target framework element is a valid, successful outcome (empty `targetFrameworks`), not a failure.
- A `global.json` with no `sdk` key is omitted from `sdks`, not reported as an error.
- Run unit tests before deployment.
