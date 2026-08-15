# C4 PR Creator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/c4-pr-creator/`.
- Validate every C4 output and repository-relative target directory before making GitHub API calls.
- Publish C4 JSON, draw.io diagrams, and an optional shared manifest update in one commit and one pull request.
- Never approve, merge, or delete pull requests or branches.
- Use only `GITHUB_PR_TOKEN`; never return or log it.
- Run unit tests before deployment.
