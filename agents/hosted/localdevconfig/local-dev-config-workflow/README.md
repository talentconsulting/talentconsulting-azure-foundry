# Local Dev Config Workflow

Hosted Foundry agent that coordinates local development configuration discovery, generation, and optional publication for one repository.

For manifest runs, `deferPublication` is `true`: the workflow calls `local-dev-config-source-discovery`, passes its validated file bundle to `local-dev-config-generator` in batches of `LOCAL_DEV_CONFIG_GENERATOR_BATCH_SIZE` (default 5), up to `LOCAL_DEV_CONFIG_GENERATOR_CONCURRENCY` batches at once (default 3); each failed batch is retried with exponential backoff, and catalogs are merged in file order regardless of completion order. The merged catalog is returned to the manifest orchestrator. The manifest orchestrator aggregates all successful repositories and calls the PR creator once.

## Input

```json
{
  "sourceUrl": "https://github.com/owner/repository/tree/main/path",
  "deferPublication": true
}
```

For a direct run, omit `deferPublication` and provide `targetRepository`. Optional publication fields are `targetDirectory`, `targetBaseBranch`, `branchName`, `pullRequestTitle`, and `pullRequestBody`.

A repository that needs zero local services is a valid, successful outcome: an empty `localDevConfigFiles` discovery result short-circuits the generator entirely and produces an empty catalog (`localServices: []`, `configurationKeys: []`).

## Output

The response reports discovery/generation success, the merged local-dev-config catalog, publication status, and stable errors. Deferred results include `catalogs` and never create a pull request.
