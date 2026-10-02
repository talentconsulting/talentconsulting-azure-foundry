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

The default output is `<source-repository>/event-catalog/events-and-commands.json`. Manifest runs set `deferPublication: true`; they return `catalogs` without invoking the PR creator so the manifest orchestrator can publish all changed repositories atomically. Files are sent to the generator in batches of `EVENTCATALOG_GENERATOR_BATCH_SIZE` (default 10), up to `EVENTCATALOG_GENERATOR_CONCURRENCY` batches at once (default 3); each failed batch is retried with exponential backoff, and batches are merged in file order regardless of completion order.

A repository with no candidate message/handler files, or whose selected files declare no events or commands, is a valid, successful outcome -- an empty catalog is generated and published rather than treated as a failure. Generation still fails closed on unreliable batches, though: if any selected batch errors, no partial catalog is published, the PR creator is not called, and a manifest orchestrator leaves that repository's commit hash unchanged so it is retried on the next run.

```bash
python3 -m unittest discover -s src/eventcatalog-workflow -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy eventcatalog-workflow --no-prompt
```
