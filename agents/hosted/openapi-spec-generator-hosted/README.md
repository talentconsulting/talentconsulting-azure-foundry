# talent-agent-openAI-generator

A Python hosted agent for Microsoft Foundry that scans a public GitHub tree URL, discovers ASP.NET controller endpoints, and returns one complete OpenAPI 3.1 specification for every route-bearing controller it finds.

The scanner performs the repository traversal and endpoint census deterministically. The configured model enriches each specification, while the agent restores any enumerated method and route omitted by the model.

## Input and output

Send exactly one source entry point:

```json
{
  "sourceUrl": "https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server"
}
```

The URL defines the GitHub owner, repository, branch or ref, and base path. The agent recursively scans beneath that path. It does not switch to another branch or scan outside the supplied base path.

The response is a single JSON object:

```json
{
  "scannedFiles": [
    "src/TalentSuite.Server/Bids/Controllers/BidsController.cs"
  ],
  "specs": [
    {
      "domain-api": "bids-api",
      "open-api": {
        "openapi": "3.1.0",
        "info": {
          "title": "Bids API",
          "version": "1.0.0"
        },
        "paths": {}
      },
      "serviceName": "Bids API",
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "fileName": "bids-api.json",
      "contentType": "application/json"
    }
  ]
}
```

There is one `specs` entry per `scannedFiles` entry. Infrastructure-only health controllers are excluded when application controllers are present.

## Project structure

```text
agents/hosted/openapi-spec-generator-hosted/
├── azure.yaml
└── src/
    └── talent-agent-openAI-generator/
        ├── main.py
        ├── github_scanner.py
        ├── spec_generator.py
        ├── test_github_scanner.py
        ├── requirements.txt
        └── eval.yaml
```

- `main.py` hosts the OpenAI Responses-compatible agent server.
- `github_scanner.py` validates the URL, downloads the public repository archive, inventories controllers, and extracts ASP.NET HTTP attributes and routes.
- `spec_generator.py` normalizes model output and guarantees that the deterministic endpoint ledger is represented.
- `azure.yaml` defines the hosted Foundry service and Python 3.13 runtime.

## Prerequisites

- Python 3.13 for parity with the hosted runtime. On macOS, use `python3`, not `python`.
- [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- Azure access to the configured Foundry project
- A deployed model, currently `gpt-4o`

Install the Foundry extensions and authenticate:

```bash
azd extension install azure.ai.agents
azd extension install azure.ai.projects
azd extension install microsoft.foundry
azd auth login
```

## Run locally with azd

From this directory:

```bash
# Run this once if the checkout has no selected azd environment.
azd env new dev --no-prompt

azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME gpt-4o
azd ai agent run talent-agent-openAI-generator
```

Keep that process running. In another terminal, invoke it:

```bash
azd ai agent invoke talent-agent-openAI-generator --local \
'{"sourceUrl":"https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server"}'
```

The local server listens on `http://localhost:8088`.

## Run directly with Python

From `src/talent-agent-openAI-generator`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

export FOUNDRY_PROJECT_ENDPOINT="https://talent-day-foundry.services.ai.azure.com/api/projects/talent-day-proj-default"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4o"

python3 main.py
```

`DefaultAzureCredential` is used locally, so sign in with `az login` or provide another supported Azure credential.

## Invoke the deployed agent

From this directory:

```bash
azd ai agent invoke talent-agent-openAI-generator \
'{"sourceUrl":"https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server"}'
```

The deployed Foundry agent is also named `talent-agent-openAI-generator`.

## Test

```bash
python3 -m unittest discover \
  -s src/talent-agent-openAI-generator \
  -p 'test_*.py'
```

## Deploy

```bash
azd deploy talent-agent-openAI-generator --no-prompt
```

Deployment creates a new immutable agent version. Verify it with:

```bash
azd ai agent show talent-agent-openAI-generator --output json
```

GitHub Actions deploys changes through [`deploy-openai-specs-generator.agent.yml`](../.github/workflows/deploy-openai-specs-generator.agent.yml).

## Evaluation

The generated evaluation configuration is stored at `src/talent-agent-openAI-generator/eval.yaml`.

After asynchronous dataset and evaluator generation finishes, run:

```bash
azd ai agent eval run
```

## Repository access

The current scanner supports public GitHub repositories through credential-free tree URLs. Private repository archive authentication is not currently implemented.

## Operational limits

- Only credential-free HTTPS `github.com` tree URLs are accepted.
- Repository archives are limited to 100 MiB compressed and 250 MiB uncompressed.
- Build, test, package, generated, and editor directories are ignored.

For hosted-agent concepts and operations, see [Microsoft Foundry hosted agents](https://learn.microsoft.com/azure/ai-foundry/agents/concepts/hosted-agents).
