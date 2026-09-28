# Database Schema Workflow

Hosted Foundry agent that coordinates database-schema generation and optional publication.

For manifest runs, `deferPublication` is `true`: the workflow calls `dbschema-source-discovery`, passes its validated file bundle to `dbschema-generator`, and returns the validated schema to the manifest orchestrator. Files are sent to the generator in batches of `DBSCHEMA_GENERATOR_BATCH_SIZE` (default 5), up to `DBSCHEMA_GENERATOR_CONCURRENCY` batches at once (default 3); each failed batch is retried with exponential backoff, and batches are merged in file order regardless of completion order. The manifest orchestrator aggregates all successful repositories and calls the PR creator once.

## Input

```json
{
  "sourceUrl": "https://github.com/owner/repository/tree/main/path",
  "deferPublication": true
}
```

For a direct run, omit `deferPublication` and provide `targetRepository`. Optional publication fields are `targetDirectory`, `targetBaseBranch`, `branchName`, `pullRequestTitle`, and `pullRequestBody`.

## Output

The response reports generation success, the generated schema, publication status, and stable errors. Deferred results include `schemas` and never create a pull request.
