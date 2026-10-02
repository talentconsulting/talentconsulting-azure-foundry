# C4 Manifest Orchestrator

Reads a shared public GitHub manifest, selects only `c4` nodes, compares branch-head commits, runs complete deferred C4 workflows, and publishes generated diagrams plus updated commit hashes in one pull request. Up to `C4_MANIFEST_WORKFLOW_CONCURRENCY` workflows (default 4) run at once; results are still processed in manifest order, so the PR content and manifest hashes do not depend on which repository finishes first.

```json
{"sourceUrl":"https://github.com/talentconsulting/service-catalogue-data/blob/main/manifest.json"}
```

Manifest node:

```json
{
  "c4": {
    "path-to-scan": "tree/main/src",
    "last-commit-hash-scanned": ""
  }
}
```

```bash
python3 -m unittest discover -s src/c4-manifest-orchestrator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy c4-manifest-orchestrator --no-prompt
```
