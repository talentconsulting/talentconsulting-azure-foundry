# Deploying the Repository Change Detector Agent

## Folder Structure

```text
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

.github/
└── workflows/
    └── deploy-repository-change-detector.yml
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

Deploy:

```bash
python scripts/deploy-agent.py --agent-dir agents/repository-change-detector
```

To force creation of a new version/agent rather than trying to update:

```bash
python scripts/deploy-agent.py --agent-dir agents/repository-change-detector --create-new-version
```

## GitHub Actions Deployment

Add the following repository secrets:

| Secret | Description |
|---|---|
| `AZURE_CLIENT_ID` | Federated identity app/client ID used by GitHub Actions |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint |

The workflow deploys automatically when files under `agents/repository-change-detector/`, `scripts/deploy-agent.py`, or the workflow itself change.

You can also run it manually using `workflow_dispatch`.

## Notes

The split files are the source of truth for maintainability.

The deploy script assembles:

- `manifest.yaml`
- `instructions.md`
- `guardrails.md`
- `tools.yaml`

into the deployed Azure AI Foundry agent definition.

`evaluations.md` and `release-notes.md` are retained for governance and review but are not deployed into the live agent by default.
