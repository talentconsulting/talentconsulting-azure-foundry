# openapi-spec-workflow-hosted

A production hosted Microsoft Foundry workflow that orchestrates:

1. `talent-openapi-file-scan` for deterministic API and payload-file discovery.
2. `openapi-spec-generator` once for every returned API file object, including its authoritative `payloadFiles` mapping.
3. Deterministic validation and aggregation of all generated OpenAPI specifications.

## Input

```json
{
  "sourceDirectoryUrl": "https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server/Bids/Controllers"
}
```

## Output

```json
{
  "success": true,
  "sourceDirectoryUrl": "https://github.com/owner/repository/tree/main/src",
  "apiFiles": [
    {
      "apiFilePath": "src/Controller.cs",
      "payloadFiles": {
        "src/Contracts/Request.cs": ["Request"]
      }
    }
  ],
  "specs": [],
  "errors": []
}
```

`specs` contains one validated response from `openapi-spec-generator` for each successful API file. The generator receives the controller URL plus the exact payload paths and DTO names from `payloadFiles`; it does not rediscover supporting files. Results retain file-scan order. Up to four generator calls run concurrently by default, and malformed or transient downstream responses are retried once.

## Local development

```bash
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-4o
azd ai agent run openapi-spec-workflow-hosted
```

In another terminal:

```bash
azd ai agent invoke openapi-spec-workflow-hosted --local \
'{"sourceDirectoryUrl":"https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server/Bids/Controllers"}'
```

## Tests

```bash
python3 -m unittest discover \
  -s src/openapi-spec-workflow-hosted \
  -p 'test_*.py'
```

## Deploy

```bash
azd deploy openapi-spec-workflow-hosted --no-prompt
```

The hosted agent identity needs the `Foundry Agent Consumer` role at the Foundry project scope so it can invoke `talent-openapi-file-scan` and `openapi-spec-generator`.

The repository action `.github/workflows/deploy-openapi-spec-workflow-hosted.agent.yml`
deploys changes pushed to the default branch. It uses the existing Azure federated
login secrets and supports repository variables for the resource group, Foundry
account, project, region, and model deployment.

## Invoke the deployed workflow

```bash
azd ai agent invoke openapi-spec-workflow-hosted \
  '{"sourceDirectoryUrl":"https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server/Bids/Controllers"}'
```
