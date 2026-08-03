# API Source Discovery

A deterministic Python hosted agent that inventories ASP.NET API files and the DTO source files used by their request and response payloads.

## Input

The input must be a JSON object with exactly one property. `sourceUrl` is the full credential-free GitHub tree URL and therefore carries the repository, ref, and path in one value:

```json
{
  "sourceUrl": "https://github.com/owner/repository/tree/main/src/Application"
}
```

API discovery is limited to the supplied path. Supporting DTO definitions may be elsewhere in the same repository at the same ref.

## Output

The response is a root JSON array. `apiFile` and every `supportingFiles` entry are absolute GitHub blob URLs at the input ref:

```json
[
  {
    "apiFile": "https://github.com/owner/repository/blob/main/src/Application/Controllers/BidsController.cs",
    "supportingFiles": [
      "https://github.com/owner/repository/blob/main/src/Application/Contracts/BidResponse.cs",
      "https://github.com/owner/repository/blob/main/src/Application/Contracts/CreateBidRequest.cs"
    ]
  }
]
```

Results are sorted and deduplicated. A payload file is supporting context only and never becomes its own API entry. Invalid or inaccessible input returns `[]`.

## Test

```bash
python3 -m unittest discover -s src/api-source-discovery -p 'test_*.py'
```

## Local run

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent run --no-client
```

In a second terminal:

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent invoke api-source-discovery --local \
  '{"sourceUrl":"https://github.com/owner/repository/tree/main/src/Application"}'
```

## Deploy

After selecting an existing Foundry project or provisioning a new one:

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy api-source-discovery --no-prompt
```

## GitHub deployment workflow

The root workflow `.github/workflows/deploy-api-source-discovery.agent.yml` runs the unit tests, deploys a new hosted-agent version, verifies its status, and invokes it with a contract smoke test. It runs when this agent changes on the repository's default branch and can also be started manually.

Create a GitHub environment named `dev` and add these environment secrets:

- `AZURE_CLIENT_ID`: client ID of the Entra application or managed identity used by GitHub OIDC
- `AZURE_TENANT_ID`: Azure tenant ID
- `AZURE_SUBSCRIPTION_ID`: Azure subscription ID
- `AZURE_AI_PROJECT_ENDPOINT`: full endpoint of the existing Foundry project

The OIDC identity needs `Contributor` and `Foundry User` access on the target Foundry project. Its federated credential must trust the `dev` GitHub environment.

These optional GitHub environment variables override the workflow defaults:

- `AZURE_LOCATION` (default `uksouth`)
- `AZURE_RESOURCE_GROUP` (default `talent-day-rg`)
- `AZURE_AI_ACCOUNT_NAME` (default `talent-day-foundry`)
- `AZURE_AI_PROJECT_NAME` (default `talent-day-proj-default`)
- `API_SOURCE_DISCOVERY_TEST_URL`: public GitHub tree URL used by the post-deployment smoke test
