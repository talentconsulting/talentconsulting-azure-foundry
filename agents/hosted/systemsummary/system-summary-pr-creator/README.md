# System Summary PR Creator

Publishes one generated `system-summaries.json` file through the GitHub API. Simpler than `dbschema-pr-creator`/`eventcatalog-pr-creator`: it always writes exactly one file, since `system-summary-manifest-orchestrator` combines every repository's summary before calling this agent.

```json
{"repository": "owner/repository", "targetPath": "system-summaries.json", "fileContent": {"systems": [...]}}
```

```bash
python3 -m unittest discover -s src/system-summary-pr-creator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy system-summary-pr-creator --no-prompt
```
