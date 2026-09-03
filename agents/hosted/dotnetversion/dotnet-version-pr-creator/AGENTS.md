# .NET Version PR Creator

This project was built with the microsoft-foundry skill. Before working on or answering questions about Foundry agents, read the microsoft-foundry skill first.

- Keep runtime code under `src/dotnet-version-pr-creator/`.
- Never commit GitHub credentials; read `GITHUB_PR_TOKEN` from the environment.
- Commit every supplied catalog and optional manifest update together, then create at most one branch and pull request.
- Never approve or merge a pull request.
- Run the unit tests before deployment.
