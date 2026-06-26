# AI Source Control Template

This repository is a source-control example for storing, reviewing, and deploying AI agents and related governance evidence.

The current template contains one deployable Azure AI Foundry agent: `repository-change-detector`. The agent identifies repositories where a manifest entry is missing `latestCommit` or where `latestCommit` is out of date compared with GitHub.

## Repository Structure

```text
.
├── .env.example
├── .github/
│   └── workflows/
│       └── deploy-repository-change-detector.yml
├── agents/
│   └── repository-change-detector/
│       ├── evaluations.md
│       ├── guardrails.md
│       ├── instructions.md
│       ├── manifest.yaml
│       ├── release-notes.md
│       └── tools.yaml
├── scripts/
│   └── deploy-agent.py
├── CODEOWNERS
├── CONTRIBUTING.md
├── DEPLOYMENT.md
├── README.md
└── requirements-agent-deploy.txt
```

## What Each Area Contains

| Path | Purpose |
| --- | --- |
| `.github/workflows/` | GitHub Actions workflow for deploying the agent. |
| `agents/repository-change-detector/manifest.yaml` | Agent metadata, model configuration, inputs, outputs, and file references. |
| `agents/repository-change-detector/instructions.md` | Core task instructions for the agent. |
| `agents/repository-change-detector/tools.yaml` | Tool definitions and permissions used by the agent. |
| `agents/repository-change-detector/guardrails.md` | Read-only, data-access, output, and failure-behaviour controls. |
| `agents/repository-change-detector/evaluations.md` | Governance and quality checks for expected behaviour. |
| `agents/repository-change-detector/release-notes.md` | Release history and operational notes. |
| `scripts/deploy-agent.py` | Deployment script that assembles the split agent files and deploys to Azure AI Foundry. |
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

Force creation of a new agent or version:

```bash
python scripts/deploy-agent.py --agent-dir agents/repository-change-detector --create-new-version
```

## GitHub Actions Deployment

The workflow is stored at:

```text
.github/workflows/deploy-repository-change-detector.yml
```

Required repository secrets:

| Secret | Description |
| --- | --- |
| `AZURE_CLIENT_ID` | Federated identity app/client ID used by GitHub Actions. |
| `AZURE_TENANT_ID` | Azure tenant ID. |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID. |
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint. |

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full deployment guide.

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
