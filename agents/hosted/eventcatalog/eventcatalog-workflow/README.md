# Event and Command Catalog Workflow

Coordinates deterministic discovery, bounded model generation, catalog merging, and optional PR publication for one public GitHub directory.

For a direct run:

```json
{
  "sourceUrl": "https://github.com/owner/repository/tree/main/src/Application",
  "targetRepository": "owner/architecture-catalogue",
  "targetDirectory": "repository/event-catalog",
  "targetBaseBranch": "main"
}
```

The default output is `<source-repository>/event-catalog/events-and-commands.json`. Manifest runs set `deferPublication: true`; they return `catalogs` without invoking the PR creator so the manifest orchestrator can publish all changed repositories atomically.

Generation is fail-closed: every selected batch must succeed and the merged result must contain at least one event or command. Otherwise no catalog is returned, the PR creator is not called, and a manifest orchestrator leaves that repository's commit hash unchanged.

```bash
python3 -m unittest discover -s src/eventcatalog-workflow -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy eventcatalog-workflow --no-prompt
```
