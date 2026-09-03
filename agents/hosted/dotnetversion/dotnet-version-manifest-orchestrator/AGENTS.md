# .NET Version Manifest Orchestrator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/dotnet-version-manifest-orchestrator/`.
- Preserve the exact one-property `sourceUrl` input contract.
- Select only the `dotnet-version` node from shared manifest entries and ignore unrelated nodes and entries.
- Invoke `dotnet-version-workflow` once per changed repository with publication deferred.
- Treat a workflow result with empty `projects`/`sdks` as a valid success, not a failure.
- Update commit hashes only for repositories whose complete dotnet-version generation succeeds.
- Publish all successful catalogs and the updated manifest in one pull request.
- Do not add a schedule until one is explicitly requested.
- Run unit tests before deployment.
