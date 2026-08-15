# C4 PR Creator

Commits up to 100 validated C4 outputs plus an optional manifest update in one GitHub commit, then opens one pull request. Each C4 output writes `c4.json`, `context.drawio`, and `container.drawio`. Unchanged content creates neither a branch nor a pull request. The hosted service reuses the `openapi-pr-github` Foundry custom-keys connection.

```bash
python3 -m unittest discover -s src/c4-pr-creator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy c4-pr-creator --no-prompt
```
