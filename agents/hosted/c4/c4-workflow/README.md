# C4 Workflow

Coordinates deterministic source discovery, model-backed C4 generation, validation, and optional pull-request publication for one repository path. Publication writes editable draw.io context and container diagrams plus canonical C4 JSON.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src","targetRepository":"owner/service-catalogue-data"}
```

Set `deferPublication` to `true` when called by the manifest orchestrator.

```bash
python3 -m unittest discover -s src/c4-workflow -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy c4-workflow --no-prompt
```
