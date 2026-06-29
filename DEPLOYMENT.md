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
.github/workflows/deploy-repository-change-detector.yml
```

GitHub Actions will not discover workflows under the `agents/` folder.

Add these repository secrets:

| Secret | Description |
|---|---|
| `AZURE_CLIENT_ID` | Federated identity app/client ID used by GitHub Actions |
| `AZURE_TENANT_ID` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint |

This workflow uses the GitHub environment `dev`. If the values are stored as environment secrets, create them under `Settings` -> `Environments` -> `dev` -> `Environment secrets`. If you store them as repository secrets instead, remove `environment: dev` from the workflow or keep duplicate values in the environment.

If `azure/login` fails with `Not all values are present`, at least one of `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, or `AZURE_SUBSCRIPTION_ID` is missing, empty, or named differently in the repository or environment secrets.

For GitHub OpenID Connect authentication, the app registration or managed identity must also have a federated credential that trusts this repository and branch or environment.

## Creating `AZURE_CLIENT_ID`

`AZURE_CLIENT_ID` is the Application client ID from a Microsoft Entra app registration, or the client ID from a user-assigned managed identity. For this workflow, use a Microsoft Entra app registration with GitHub OpenID Connect unless your organisation has standardised on managed identities.

### Azure Portal

1. Go to Microsoft Entra ID.
2. Open App registrations.
3. Select New registration.
4. Name it, for example `github-ai-agent-deploy`.
5. Leave supported account types as single tenant unless your organisation requires otherwise.
6. Select Register.
7. Copy Application client ID. Add it to GitHub as `AZURE_CLIENT_ID`.
8. Copy Directory tenant ID. Add it to GitHub as `AZURE_TENANT_ID`.
9. In Azure Subscriptions, copy the subscription ID. Add it to GitHub as `AZURE_SUBSCRIPTION_ID`.

Then create a federated credential on the app registration:

1. Open the app registration.
2. Go to Certificates and secrets.
3. Open Federated credentials.
4. Select Add credential.
5. Choose GitHub Actions deploying Azure resources.
6. Enter the GitHub organisation, repository, entity type, and branch or environment used by the workflow.
7. Save the credential.

Finally, grant the app registration the required Azure RBAC role on the target resource group, Azure AI Foundry project resources, or subscription scope.

### Azure CLI

Set these values first:

```bash
subscription_id="<azure-subscription-id>"
resource_group="<target-resource-group>"
github_org="<github-org-or-user>"
github_repo="<github-repo-name>"
branch="main"
app_name="github-ai-agent-deploy"
```

Create the app registration and service principal:

```bash
app_id=$(az ad app create --display-name "$app_name" --query appId -o tsv)
az ad sp create --id "$app_id"
```

Create the federated credential for GitHub Actions on `main`:

```bash
az ad app federated-credential create \
  --id "$app_id" \
  --parameters "{\"name\":\"github-main\",\"issuer\":\"https://token.actions.githubusercontent.com\",\"subject\":\"repo:${github_org}/${github_repo}:ref:refs/heads/${branch}\",\"audiences\":[\"api://AzureADTokenExchange\"]}"
```

Grant Azure RBAC access. Start with the narrowest scope that lets the deployment update the agent:

```bash
az role assignment create \
  --assignee "$app_id" \
  --role "Azure AI Developer" \
  --scope "/subscriptions/${subscription_id}/resourceGroups/${resource_group}"
```

Add these GitHub repository secrets:

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | `$app_id` |
| `AZURE_TENANT_ID` | Output from `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | `$subscription_id` |
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
