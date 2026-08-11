# Service Dependency Manifest Orchestrator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/service-dependency-manifest-orchestrator/`.
- Preserve the exact one-property `sourceUrl` input contract.
- Select only the `service-dependencies` node from shared manifest entries and ignore unrelated nodes and entries.
- Invoke `service-dependency-workflow` once per changed repository with publication deferred.
- Update commit hashes only for repositories whose complete catalog generation succeeds.
- Publish all successful catalogs and the updated manifest in one pull request.
- Do not add a schedule until one is explicitly requested.
- Run unit tests before deployment.
