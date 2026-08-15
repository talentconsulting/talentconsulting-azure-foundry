# System Summary Manifest Orchestrator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/system-summary-manifest-orchestrator/`.
- Read the manifest and every repository's catalogs from the same service-catalogue repository; never scan a target repository's raw source.
- Call `system-summary-generator` once per manifest entry; a failing entry must not block the others.
- In deferred mode, return every generated summary without invoking the PR creator.
- In direct mode, publish one combined `system-summaries.json` through `system-summary-pr-creator` and never write to GitHub directly.
- Run the unit tests before deployment.
