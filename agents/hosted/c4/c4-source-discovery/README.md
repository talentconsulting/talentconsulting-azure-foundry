# C4 Source Discovery

Deterministically selects source, configuration, dependency, and infrastructure files that can evidence C4 context and container diagrams beneath one public GitHub tree URL. It returns bounded same-repository blob URLs and exclusions; no model is used.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src"}
```

```bash
python3 -m unittest discover -s src/c4-source-discovery -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy c4-source-discovery --no-prompt
```
