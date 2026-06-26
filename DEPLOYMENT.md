# Azure AI Agent Framework Deployment

## Directory Structure

```text
.github/
└── workflows/
    └── deploy-agents.yml

agents/
└── repository-change-detector/
    ├── manifest.yaml
    ├── instructions.md
    ├── tools.yaml
    ├── guardrails.md
    ├── evaluations.md
    └── release-notes.md

scripts/
└── deploy-agent.py

requirements-agent-deploy.txt
```

## Local Deployment

Install dependencies:

```bash
pip install -r requirements-agent-deploy.txt
```

Set your Azure AI Foundry project endpoint:

```bash
export AZURE_AI_PROJECT_ENDPOINT="https://<your-ai-service>.services.ai.azure.com/api/projects/<your-project>"
```

Deploy one agent:

```bash
python scripts/deploy-agent.py --agent-dir agents/repository-change-detector
```

Force creation of a new agent/version:

```bash
python scripts/deploy-agent.py --agent-dir agents/repository-change-detector --create-new-version
```

## GitHub Actions Deployment

The workflow must live here:

```text
.github/workflows/deploy-agents.yml
```

GitHub Actions will not discover workflows under the `agents/` folder.

Add these repository secrets:

| Secret | Description |
|---|---|
| `AZURE_CLIENT_ID` | Federated identity app/client ID used by GitHub Actions |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint |

## Automatic Deployment

On push to `main`, the workflow detects changed folders under `agents/` and deploys only those agents.

Example changed file:

```text
agents/repository-change-detector/instructions.md
```

Deploy command run by the workflow:

```bash
python scripts/deploy-agent.py --agent-dir agents/repository-change-detector
```

## Manual Deployment

Run the workflow manually and optionally provide:

```text
repository-change-detector
```

as the `agent_name` input.

## Notes

- `manifest.yaml`, `instructions.md`, `guardrails.md`, and `tools.yaml` are assembled into the deployed Azure AI Foundry agent.
- `evaluations.md` and `release-notes.md` are kept for governance and review.
- This structure supports adding more agents under the `agents/` folder without creating more workflow files.
