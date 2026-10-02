# .NET Version Workflow

Hosted Foundry agent that coordinates .NET version discovery, generation, and optional publication for one repository.

For manifest runs, `deferPublication` is `true`: the workflow calls `repo-metadata-source-discovery`, passes its validated file bundle to `repo-metadata-generator` in batches of `REPO_METADATA_GENERATOR_BATCH_SIZE` (default 5), up to `REPO_METADATA_GENERATOR_CONCURRENCY` batches at once (default 3); each failed batch is retried with exponential backoff, and batches are merged in file order regardless of completion order. The merged catalog is returned to the manifest orchestrator. The manifest orchestrator aggregates all successful repositories and calls the PR creator once.

## Input

```json
{
  "sourceUrl": "https://github.com/owner/repository/tree/main/path",
  "deferPublication": true
}
```

For a direct run, omit `deferPublication` and provide `targetRepository`. Optional publication fields are `targetDirectory`, `targetBaseBranch`, `branchName`, `pullRequestTitle`, and `pullRequestBody`.

A repository with no `.csproj` or `global.json` files is a valid, successful outcome: an empty `repoMetadataFiles` discovery result short-circuits the generator entirely and produces an empty catalog (`projects: []`, `sdks: []`, `dotnetSupport: []`).

## Output

The response reports discovery/generation success, the merged .NET version catalog, publication status, and stable errors. Deferred results include `catalogs` and never create a pull request.
