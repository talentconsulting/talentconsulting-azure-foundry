# AI Source Control Template

This repository is a source-control example for storing, reviewing, deploying, and running AI agents and related governance evidence.

The current template contains deployable Azure AI Foundry agents, including `repository-change-detector`. That agent identifies repositories where a manifest entry is missing `latestCommit` or where `latestCommit` is out of date compared with GitHub.

## Repository Structure

```text
.
├── .env.example
├── .github/
│   └── workflows/
│       ├── deploy-openapi-spec-reviewer.agent.yml
│       ├── deploy-openai-specs-generator.agent.yml
│       ├── deploy-repository-file-pr-creator.agent.yml
│       ├── deploy-repository-change-detector.agent.yml
│       └── run-service-catalogue-agent-chain.yml
├── agents/
│   ├── openapi-spec-reviewer/
│   │   ├── evaluations.md
│   │   ├── guardrails.md
│   │   ├── instructions.md
│   │   ├── manifest.yaml
│   │   ├── release-notes.md
│   │   └── tools.yaml
│   ├── openapi-specs-generator/
│   │   ├── evaluations.md
│   │   ├── guardrails.md
│   │   ├── instructions.md
│   │   ├── manifest.yaml
│   │   ├── release-notes.md
│   │   └── tools.yaml
│   ├── repository-change-detector/
│   │   ├── evaluations.md
│   │   ├── guardrails.md
│   │   ├── instructions.md
│   │   ├── manifest.yaml
│   │   ├── release-notes.md
│   │   └── tools.yaml
│   └── repository-file-pr-creator/
│       ├── evaluations.md
│       ├── guardrails.md
│       ├── instructions.md
│       ├── manifest.yaml
│       ├── release-notes.md
│       └── tools.yaml
├── scripts/
│   ├── deploy-agent.py
│   ├── validate-workflow.py
│   └── run-ai-source-control-workflow.py
├── workflows/
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
| `agents/repository-change-detector/manifest.yaml` | Agent metadata, model configuration, inputs, outputs, and file references. |
| `agents/repository-change-detector/instructions.md` | Core task instructions for the agent. |
| `agents/repository-change-detector/tools.yaml` | Tool definitions and permissions used by the agent. |
| `agents/repository-change-detector/guardrails.md` | Read-only, data-access, output, and failure-behaviour controls. |
| `agents/repository-change-detector/evaluations.md` | Governance and quality checks for expected behaviour. |
| `agents/repository-change-detector/release-notes.md` | Release history and operational notes. |
| `agents/openapi-specs-generator/` | Agent source for generating OpenAPI specifications from API repositories. |
| `agents/openapi-spec-reviewer/` | Agent source for reviewing generated OpenAPI specifications. |
| `agents/repository-file-pr-creator/` | Agent source for creating branches, writing structured file content, and opening pull requests. |
| `scripts/deploy-agent.py` | Deployment script that assembles the split agent files and deploys to Azure AI Foundry. |
| `scripts/validate-workflow.py` | Validates the source-controlled workflow manifest and referenced agents. |
| `scripts/run-ai-source-control-workflow.py` | Runtime script that invokes the repository-change detector first, then runs OpenAPI generation and pull request creation for changed repositories. |
| `workflows/service-catalogue/manifest.yaml` | Governance/source-control metadata for the chained workflow. |
| `requirements-agent-deploy.txt` | Python dependencies for local and CI deployment. |
| `DEPLOYMENT.md` | Deployment setup, GitHub Actions secrets, and local deployment commands. |
| `CONTRIBUTING.md` | Change-control, review, versioning, release, and retirement guidance. |
| `CODEOWNERS` | Default ownership rules for repository review. |

## Agent Source Pattern

Each agent should live under `agents/<agent-name>/` and keep deployable behaviour separate from governance evidence:

```text
agents/<agent-name>/
├── manifest.yaml       # Required deployment metadata
├── instructions.md     # Required runtime instructions
├── tools.yaml          # Required tool definitions
├── guardrails.md       # Required safety and operating controls
├── evaluations.md      # Required test and review evidence
└── release-notes.md    # Required release history
```

This keeps AI behaviour reviewable in pull requests and gives governance standards a stable place to reference approved instructions, tools, evaluations, and release evidence.

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
python scripts/deploy-agent.py --agent-dir agents/repository-change-detector
```

Or:

```bash
python scripts/deploy-agent.py --agent-dir agents/openapi-specs-generator
```

Or:

```bash
python scripts/deploy-agent.py --agent-dir agents/openapi-spec-reviewer
```

Or:

```bash
python scripts/deploy-agent.py --agent-dir agents/repository-file-pr-creator
```

Force creation of a new agent or version:

```bash
python scripts/deploy-agent.py --agent-dir agents/repository-change-detector --create-new-version
```

Validate the service catalogue workflow source:

```bash
python scripts/validate-workflow.py --workflow-dir workflows/service-catalogue
```

## GitHub Actions Deployment

Deployment workflows are stored at:

```text
.github/workflows/deploy-openapi-spec-reviewer.agent.yml
.github/workflows/deploy-openai-specs-generator.agent.yml
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

Optional repository secrets:

| Secret | Description |
| --- | --- |
| `SOURCE_GITHUB_TOKEN` | GitHub token with read access to source repositories scanned by the workflow. Use this when the manifest references private repositories outside the workflow repository. |

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full deployment guide.

## Chained Workflow

Use `.github/workflows/run-service-catalogue-agent-chain.yml` to run the service catalogue chain from GitHub Actions. This calls the deployed Foundry agents one at a time from `scripts/run-ai-source-control-workflow.py`, passing only the validated JSON output needed by the next step. The runner scans changed repositories for API source files, invokes the OpenAPI generator once per discovered controller file, then creates pull requests in the manifest repository supplied to the detector.

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
