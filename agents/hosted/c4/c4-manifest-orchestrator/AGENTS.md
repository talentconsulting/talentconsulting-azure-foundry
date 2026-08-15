# C4 Manifest Orchestrator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/c4-manifest-orchestrator/`.
- Preserve the exact one-property `sourceUrl` input contract.
- Select only the `c4` node from shared manifest entries and ignore unrelated nodes and entries.
- Invoke `c4-workflow` once per changed repository with publication deferred.
- Update commit hashes only for repositories whose complete C4 generation succeeds.
- Publish all successful C4 outputs and the updated manifest in one pull request.
- Do not add a schedule until one is explicitly requested.
- Run unit tests before deployment.
