# System Summary Manifest Orchestrator

Hosted Foundry agent that reads the service-catalogue's own `manifest.json`, and for every listed repository reads whichever of its already-published catalogs exist (`db-schema`, `event-catalog`, `service-dependencies`, `open-api`). It calls `system-summary-generator` once per repository — up to `SYSTEM_SUMMARY_MANIFEST_WORKFLOW_CONCURRENCY` repositories (default 4) at once, with results still processed in manifest order so the published file does not depend on which repository finishes first — and publishes one combined `system-summaries.json` through `system-summary-pr-creator`.

Unlike the dbschema/eventcatalog/service-dependency orchestrators, this agent never scans a target repository's raw source and never updates commit-hash tracking in the manifest — summaries are regenerated for every listed repository on each run.

## Input

```json
{"sourceUrl": "https://github.com/owner/repository/blob/main/manifest.json"}
```

Pass `"deferPublication": true` to return the generated summaries without opening a pull request.

## Output

Reports how many repositories were checked, how many summaries were generated, any per-repository failures (which do not block the others), and the publication result.
