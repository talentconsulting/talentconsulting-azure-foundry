# AI Source Control Template

This repository is a source-control example for storing, reviewing, deploying, and running AI agents and related governance evidence.

The current template contains prompt agents, the hosted [`talent-openapi-file-scan`](agents/hosted/talent-openapi-file-scan/README.md), and the production hosted [`openapi-spec-workflow-hosted`](agents/hosted/openapi-spec-workflow-hosted/README.md). The file scan inventories each API source file and its request/response DTO source files; the workflow then invokes the single-file generator with that exact payload context.

## Repository Structure

```text
.
├── .env.example
├── .github/
│   └── workflows/
│       ├── deploy-openapi-spec-reviewer.agent.yml
│       ├── deploy-openapi-spec-generator.agent.yml
│       ├── deploy-openapi-spec-workflow-hosted.agent.yml
│       ├── deploy-talent-openapi-file-scan.agent.yml
│       ├── deploy-repository-file-pr-creator.agent.yml
│       ├── deploy-repository-change-detector.agent.yml
│       ├── run-openapi-spec-generation.yml
│       └── run-service-catalogue-agent-chain.yml
├── agents/
│   ├── hosted/
│   │   ├── talent-openapi-file-scan/
│   │   │   ├── azure.yaml
│   │   │   └── src/
│   │   │       └── talent-openapi-file-scan/
│   │   │           ├── main.py
│   │   │           ├── github_scanner.py
│   │   │           └── eval.yaml
│   │   └── openapi-spec-workflow-hosted/
│   │       ├── azure.yaml
│   │       └── src/
│   │           └── openapi-spec-workflow-hosted/
│   └── prompt/
│       ├── openapi-spec-generator/
│       ├── openapi-spec-scanner/
│       ├── openapi-spec-reviewer/
│       ├── repository-change-detector/
│       └── repository-file-pr-creator/
├── scripts/
│   ├── deploy-agent.py
│   ├── run-openapi-spec-generation-workflow.py
│   ├── validate-workflow.py
│   └── run-ai-source-control-workflow.py
├── workflows/
│   ├── openapi-spec-generation/
│   │   └── manifest.yaml
│   └── service-catalogue/
│       └── manifest.yaml
├── CODEOWNERS
├── CONTRIBUTING.md
├── DEPLOYMENT.md
├── README.md
└── requirements-agent-deploy.txt
```

## What Each Area Contains

| Path | Purpose |
| --- | --- |
| `.github/workflows/` | GitHub Actions workflows for deploying agents and running the service catalogue agent chain. |
| `agents/prompt/repository-change-detector/` | Prompt agent that identifies repositories requiring downstream processing. |
| [`agents/hosted/talent-openapi-file-scan/`](agents/hosted/talent-openapi-file-scan/README.md) | Deterministically returns API paths and a per-API mapping of payload source paths to relevant DTO types. |
| [`agents/hosted/openapi-spec-workflow-hosted/`](agents/hosted/openapi-spec-workflow-hosted/README.md) | Production orchestration that invokes the file scan and fans its API/payload objects out to `openapi-spec-generator`. |
| `agents/prompt/openapi-spec-generator/` | Prompt agent that generates one OpenAPI specification from one controller URL plus its supplied payload-file mapping. |
| `agents/prompt/openapi-spec-scanner/` | Legacy prompt scanner retained for compatibility; production workflows use `talent-openapi-file-scan`. |
| `agents/prompt/openapi-spec-reviewer/` | Prompt agent for reviewing generated OpenAPI specifications. |
| `agents/prompt/repository-file-pr-creator/` | Prompt agent for creating branches, writing structured file content, and opening pull requests. |
| `scripts/deploy-agent.py` | Deployment script that assembles the split agent files and deploys to Azure AI Foundry. |
| `scripts/validate-workflow.py` | Validates the source-controlled workflow manifest and referenced agents. |
| `scripts/run-ai-source-control-workflow.py` | Runtime script that invokes the repository-change detector first, then runs OpenAPI generation and pull request creation for changed repositories. |
| `workflows/service-catalogue/manifest.yaml` | Governance/source-control metadata for the chained workflow. |
| `requirements-agent-deploy.txt` | Python dependencies for local and CI deployment. |
| `DEPLOYMENT.md` | Deployment setup, GitHub Actions secrets, and local deployment commands. |
| `CONTRIBUTING.md` | Change-control, review, versioning, release, and retirement guidance. |
| `CODEOWNERS` | Default ownership rules for repository review. |

## Agent Source Pattern

Prompt agents live under `agents/prompt/<agent-name>/` and keep deployable behaviour separate from governance evidence:

```text
agents/prompt/<agent-name>/
├── manifest.yaml       # Required deployment metadata
├── instructions.md     # Required runtime instructions
├── tools.yaml          # Required tool definitions
├── guardrails.md       # Required safety and operating controls
├── evaluations.md      # Required test and review evidence
└── release-notes.md    # Required release history
```

This keeps AI behaviour reviewable in pull requests and gives governance standards a stable place to reference approved instructions, tools, evaluations, and release evidence.

Hosted Python agents live under `agents/hosted/<project-name>/`, with runtime code under `src/<agent-name>/`.

## Local Deployment

Install dependencies:

```bash
pip install -r requirements-agent-deploy.txt
```

Set the Azure AI Foundry project endpoint:

```bash
export AZURE_AI_PROJECT_ENDPOINT="https://<your-ai-service>.services.ai.azure.com/api/projects/<your-project>"
```

Deploy the agent:

```bash
python scripts/deploy-agent.py --agent-dir agents/prompt/repository-change-detector
```

Deploy the updated single-file generator contract:

```bash
python scripts/deploy-agent.py \
  --agent-dir agents/prompt/openapi-spec-generator \
  --create-new-version
```

Deploy the hosted API and payload file scan:

```bash
cd agents/hosted/talent-openapi-file-scan
azd deploy talent-openapi-file-scan --no-prompt
```

Deploy the hosted scanner-to-generator workflow:

```bash
cd agents/hosted/openapi-spec-workflow-hosted
azd deploy openapi-spec-workflow-hosted --no-prompt
```

Deploy these three components in that order: `talent-openapi-file-scan`, `openapi-spec-generator`, then `openapi-spec-workflow-hosted`.

Or:

```bash
python scripts/deploy-agent.py --agent-dir agents/prompt/openapi-spec-reviewer
```

Or:

```bash
python scripts/deploy-agent.py --agent-dir agents/prompt/repository-file-pr-creator
```

Force creation of a new agent or version:

```bash
python scripts/deploy-agent.py --agent-dir agents/prompt/repository-change-detector --create-new-version
```

Validate the service catalogue workflow source:

```bash
python scripts/validate-workflow.py --workflow-dir workflows/service-catalogue
```

## GitHub Actions Deployment

Deployment workflows are stored at:

```text
.github/workflows/deploy-openapi-spec-reviewer.agent.yml
.github/workflows/deploy-openapi-spec-generator.agent.yml
.github/workflows/deploy-openapi-spec-workflow-hosted.agent.yml
.github/workflows/deploy-talent-openapi-file-scan.agent.yml
.github/workflows/deploy-repository-change-detector.agent.yml
.github/workflows/deploy-repository-file-pr-creator.agent.yml
```

Required repository secrets:

| Secret | Description |
| --- | --- |
| `AZURE_CLIENT_ID` | Federated identity app/client ID used by GitHub Actions. |
| `AZURE_TENANT_ID` | Azure tenant ID. |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID. |
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint. |

See the [hosted workflow README](agents/hosted/openapi-spec-workflow-hosted/README.md) for its input, local run, test, and deployment commands. See [DEPLOYMENT.md](DEPLOYMENT.md) for the remaining prompt-agent and workflow deployment guidance.

## Chained Workflow

### Scanner-to-generator workflow

The production Azure-hosted implementation is `openapi-spec-workflow-hosted`. Invoke it with one JSON field:

```json
{
  "sourceDirectoryUrl": "https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server/Bids/Controllers"
}
```

It returns the complete `apiFiles` inventory, including `apiFilePath` and `payloadFiles` for each API, one validated generator result per successful file, and per-file errors. The GitHub workflow below remains available as a batch runner that also writes downloadable artifacts.

Use `.github/workflows/run-openapi-spec-generation.yml` to scan one GitHub directory and generate a specification for every discovered API source file. Start it with **Run workflow** and supply a full GitHub tree URL:

```text
https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server/Bids/Controllers
```

The workflow:

1. Invokes `talent-openapi-file-scan`.
2. Validates its sorted API-file objects and their payload path-to-DTO mappings.
3. Runs `openapi-spec-generator` once for every API object, passing `payloadFiles` unchanged.
4. Uploads the `openapi-spec-generation-output` artifact.

The artifact contains:

```text
file-scan-output.json
specs/
  <generated-api>.json
workflow-output.json
```

Run the same workflow locally:

```bash
python scripts/run-openapi-spec-generation-workflow.py \
  --source-directory-url "https://github.com/talentconsulting/talentsuite-bidmanager/tree/main/src/TalentSuite.Server/Bids/Controllers" \
  --output-dir outputs/openapi-spec-generation
```

### Service catalogue workflow

Use `.github/workflows/run-service-catalogue-agent-chain.yml` to run the service catalogue chain from GitHub Actions. This calls the deployed Foundry agents one at a time from `scripts/run-ai-source-control-workflow.py`, passing only validated JSON to the next step. For each changed repository, the runner constructs one GitHub tree URL and invokes `openapi-spec-workflow-hosted`. That workflow obtains the API/payload inventory from `talent-openapi-file-scan`, generates one specification per API, and returns the aggregate result used to create pull requests in the manifest repository.

The workflow chain is defined in `workflows/service-catalogue/manifest.yaml`, following the same source-controlled manifest pattern as the agents.

The GitHub runner uploads a `service-catalogue-agent-chain-output` artifact containing the detector output, generator responses, generated specs, skipped repositories, pull request results, and workflow summary. If the generator returns no specs for a repository, that repository is skipped and no pull request is created for it.

## Governance Use

This repository is intended to be linked from AI governance standards as an example of how to source-control AI assets.

It demonstrates:

- Versioned agent instructions.
- Explicit model and output-schema configuration.
- Tool access and permission documentation.
- Read-only guardrails and failure behaviour.
- Evaluation scenarios and acceptance checks.
- Deployment automation through source-controlled scripts and workflows.
- Release notes and ownership through `CODEOWNERS`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the recommended review and change-control process.
