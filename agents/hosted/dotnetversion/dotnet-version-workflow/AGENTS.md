# .NET Version Workflow

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/dotnet-version-workflow/`.
- Invoke deterministic source discovery before generation and pass only its validated file bundle to the generator, in batches.
- Merge generator batch catalogs deterministically (dedupe projects/sdks by path) before returning or publishing.
- In deferred mode, return the complete merged catalog without invoking the PR creator.
- In direct mode, publish through `dotnet-version-pr-creator` and never write to GitHub directly.
- An empty discovery result (no `.csproj`/`global.json` files found) is a valid outcome, not a failure.
- Run the unit tests before deployment.
