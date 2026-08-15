# System Summary PR Creator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/system-summary-pr-creator/`.
- Publish exactly one JSON file (`repository`, `targetPath`, `content`) per invocation through the GitHub API.
- Never write directly to a branch without going through the create-blob/tree/commit/ref/PR sequence.
- Skip opening a pull request when the target file's content is unchanged.
- Run the unit tests before deployment.
