# System Summary Manifest Orchestrator

Hosted Foundry agent that reads the service-catalogue's own `manifest.json`, and for every listed repository reads whichever of its already-published catalogs exist (`db-schema`, `event-catalog`, `service-dependencies`, `open-api`). It calls `system-summary-generator` once per repository and publishes one combined `system-summaries.json` through `system-summary-pr-creator`.

Unlike the dbschema/eventcatalog/service-dependency orchestrators, this agent never scans a target repository's raw source and never updates commit-hash tracking in the manifest — summaries are regenerated for every listed repository on each run.

## Input

```json
{"sourceUrl": "https://github.com/owner/repository/blob/main/manifest.json"}
```

Pass `"deferPublication": true` to return the generated summaries without opening a pull request.

## Output

Reports how many repositories were checked, how many summaries were generated, any per-repository failures (which do not block the others), and the publication result.
