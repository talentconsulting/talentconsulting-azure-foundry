# Service Dependency Workflow

Coordinates deterministic source discovery, model-backed service-dependency extraction, deterministic merging, validation, and optional pull-request publication for one repository path. Any failed generation batch causes the workflow to fail closed.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src","targetRepository":"owner/service-catalogue-data"}
```

Set `deferPublication` to `true` when called by the manifest orchestrator.

```bash
python3 -m unittest discover -s src/service-dependency-workflow -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy service-dependency-workflow --no-prompt
```
