# OpenAPI Spec Generator

A Python hosted agent that consumes one element returned by OpenAPI Source Discovery, reads the referenced API and DTO source files, and returns one complete OpenAPI 3.1 document as JSON.

## Input

The input must be a JSON object with exactly these properties:

```json
{
  "apiFile": "https://github.com/owner/repository/blob/main/src/Api/Controllers/BidsController.cs",
  "supportingFiles": [
    "https://github.com/owner/repository/blob/main/src/Contracts/BidResponse.cs",
    "https://github.com/owner/repository/blob/main/src/Contracts/CreateBidRequest.cs"
  ]
}
```

Every URL must be a credential-free HTTPS GitHub blob URL from the same repository and ref. The agent reads only the supplied files; it does not scan the repository for additional context.

## Output

The response is the OpenAPI document itself, not a wrapper and not Markdown:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Bids API",
    "version": "1.0.0"
  },
  "paths": {},
  "components": {
    "schemas": {}
  }
}
```

Generation failures remain valid JSON and use an `error` object instead of an incomplete specification.

## Configuration

The hosted process requires:

- `FOUNDRY_PROJECT_ENDPOINT`
- `AZURE_AI_MODEL_DEPLOYMENT_NAME`

The current shared Foundry environment uses the existing `gpt-4o` deployment.

## Test

```bash
python3 -m unittest discover -s src/openapi-spec-generator -p 'test_*.py'
```

## Local run

Create `src/openapi-spec-generator/.env` from `.env.example`, then create the virtual environment beside `requirements.txt`:

```bash
cd src/openapi-spec-generator
python3 -m venv .venv
source .venv/bin/activate
python -m pip install uv
cd ../..
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent run openapi-spec-generator --no-client
```

Invoke it from a second terminal:

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent invoke openapi-spec-generator --local \
  '{"apiFile":"https://github.com/owner/repository/blob/main/src/Api/Controllers/BidsController.cs","supportingFiles":[]}'
```

## Deploy

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy openapi-spec-generator --no-prompt
```
