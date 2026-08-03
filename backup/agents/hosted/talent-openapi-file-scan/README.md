# talent-openapi-file-scan

A Python hosted agent for Microsoft Foundry that scans a public GitHub tree URL and returns every ASP.NET API source file together with the source files defining its request and response DTOs.

The scan is deterministic. Payload files include direct action parameter and return types plus nested model dependencies. This agent inventories source files only; `openapi-spec-workflow-hosted` passes each inventory item to `openapi-spec-generator` to produce the specification.

## Input and output

Send exactly one source entry point:

```json
{
  "sourceUrl": "https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server"
}
```

The URL defines the GitHub owner, repository, branch or ref, and API base path. API controllers must be beneath that path. To resolve their payload graphs, the agent may include DTO source files elsewhere in the same repository at the exact same ref; it never switches repositories or refs.

The response is a single JSON object:

```json
{
  "apiFiles": [
    {
      "apiFilePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "payloadFiles": {
        "src/TalentSuite.Server/Bids/Contracts/CreateBidRequest.cs": [
          "CreateBidRequest"
        ],
        "src/TalentSuite.Server/Bids/Contracts/BidResponse.cs": [
          "BidResponse"
        ]
      }
    }
  ]
}
```

`apiFiles` is sorted by `apiFilePath`. Each `payloadFiles` object maps a sorted repository-relative source path to the sorted DTO type names from that file that are relevant to the API payload graph. Payload files do not create separate API entries. Infrastructure-only health controllers are excluded when application controllers are present.

## Project structure

```text
agents/hosted/talent-openapi-file-scan/
├── azure.yaml
└── src/
    └── talent-openapi-file-scan/
        ├── main.py
        ├── github_scanner.py
        ├── test_github_scanner.py
        ├── test_main.py
        ├── requirements.txt
        └── eval.yaml
```

- `main.py` hosts the OpenAI Responses-compatible agent server.
- `github_scanner.py` validates the URL, downloads the public repository archive, inventories controllers, and resolves direct and nested DTO source files.
- `azure.yaml` defines the hosted Foundry service and Python 3.13 runtime.

## Prerequisites

- Python 3.13 for parity with the hosted runtime. On macOS, use `python3`, not `python`.
- [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- Azure access to the configured Foundry project

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

azd ai agent run talent-openapi-file-scan
```

Keep that process running. In another terminal, invoke it:

```bash
azd ai agent invoke talent-openapi-file-scan --local \
'{"sourceUrl":"https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server"}'
```

The local server listens on `http://localhost:8088`.

## Run directly with Python

From `src/talent-openapi-file-scan`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

python3 main.py
```

## Invoke the deployed agent

From this directory:

```bash
azd ai agent invoke talent-openapi-file-scan \
'{"sourceUrl":"https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server"}'
```

The deployed Foundry agent is also named `talent-openapi-file-scan`.

## Test

```bash
python3 -m unittest discover \
  -s src/talent-openapi-file-scan \
  -p 'test_*.py'
```

## Deploy

```bash
azd deploy talent-openapi-file-scan --no-prompt
```

Deployment creates a new immutable agent version. Verify it with:

```bash
azd ai agent show talent-openapi-file-scan --output json
```

GitHub Actions deploys changes through [`deploy-talent-openapi-file-scan.agent.yml`](../../../.github/workflows/deploy-talent-openapi-file-scan.agent.yml).

## Evaluation

The generated evaluation configuration is stored at `src/talent-openapi-file-scan/eval.yaml`.

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
