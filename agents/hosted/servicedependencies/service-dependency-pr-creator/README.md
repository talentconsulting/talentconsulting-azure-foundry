# Service Dependency PR Creator

Commits up to 100 validated service-dependency catalogs plus an optional manifest update in one GitHub commit, then opens one pull request. Unchanged content creates neither a branch nor a pull request. The hosted service reuses the `openapi-pr-github` Foundry custom-keys connection.

```bash
python3 -m unittest discover -s src/service-dependency-pr-creator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy service-dependency-pr-creator --no-prompt
```
