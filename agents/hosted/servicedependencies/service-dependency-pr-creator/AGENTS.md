# Service Dependency PR Creator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/service-dependency-pr-creator/`.
- Validate every catalog and repository-relative target path before making GitHub API calls.
- Publish catalogs and an optional shared manifest update in one commit and one pull request.
- Never approve, merge, or delete pull requests or branches.
- Use only `GITHUB_PR_TOKEN`; never return or log it.
- Run unit tests before deployment.
