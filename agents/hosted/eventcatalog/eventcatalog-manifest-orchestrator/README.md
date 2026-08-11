# Event and Command Catalog Manifest Orchestrator

Reads a public GitHub JSON manifest, compares each configured branch head with `last-commit-hash-scanned`, invokes `eventcatalog-workflow` only for changed repositories, and creates one combined catalogs-and-manifest pull request. Successful entries advance their commit hash; failed entries remain retryable. No schedule is created.

```json
[
  {
    "github-repo": "https://github.com/owner/application",
    "eventcatalog": {
      "path-to-scan": "tree/main/src/Application",
      "last-commit-hash-scanned": ""
    }
  }
]
```

Invoke the agent with the manifest blob URL:

```json
{"sourceUrl":"https://github.com/owner/catalogue/blob/main/repoManifest.json"}
```

Unrelated manifest nodes are ignored. `event-catalog` is accepted as a legacy alias for `eventcatalog`. Each successful repository is written to `<repository>/event-catalog/events-and-commands.json` in the manifest repository.

```bash
python3 -m unittest discover -s src/eventcatalog-manifest-orchestrator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy eventcatalog-manifest-orchestrator --no-prompt
```
