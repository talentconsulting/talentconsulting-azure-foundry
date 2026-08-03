# Deployment

The pipeline uses an existing Azure AI Foundry project and four hosted agents. Deploy them in this order:

1. `openapi-source-discovery`
2. `openapi-spec-generator`
3. `openapi-spec-pr-creator`
4. `openapi-spec-workflow`

## GitHub Actions configuration

Create a GitHub environment named `dev` with these secrets:

| Secret | Used by | Purpose |
| --- | --- | --- |
| `AZURE_CLIENT_ID` | All deployments | Entra application or managed identity client ID for GitHub OIDC. |
| `AZURE_TENANT_ID` | All deployments | Azure tenant ID. |
| `AZURE_SUBSCRIPTION_ID` | All deployments | Azure subscription ID. |
| `AZURE_AI_PROJECT_ENDPOINT` | All deployments | Existing Foundry project endpoint. |

The Azure identity needs deployment access to the Foundry project. The hosted workflow identity needs permission to invoke the other agents in that project.

Create a Foundry Custom keys project connection named `openapi-pr-github` with a write-only `github_token` field. Grant that fine-grained token access only to the destination specification repository, with:

- Metadata: read
- Contents: read and write
- Pull requests: read and write

The PR creator resolves the token from `${{connections.openapi-pr-github.credentials.github_token}}` when its sandbox starts. It is not stored in the agent definition, passed to the orchestration agent, or accepted in an agent request.

Optional `dev` environment variables are:

| Variable | Default |
| --- | --- |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | `gpt-4o` |
| `AZURE_LOCATION` | `uksouth` |
| `AZURE_RESOURCE_GROUP` | `talent-day-rg` |
| `AZURE_AI_ACCOUNT_NAME` | `talent-day-foundry` |
| `AZURE_AI_PROJECT_NAME` | `talent-day-proj-default` |

## Deployment workflows

The following workflows run on changes to their agent on the default branch and support manual dispatch:

- `.github/workflows/deploy-openapi-source-discovery.agent.yml`
- `.github/workflows/deploy-openapi-spec-generator.agent.yml`
- `.github/workflows/deploy-openapi-spec-pr-creator.agent.yml`
- `.github/workflows/deploy-openapi-spec-workflow.agent.yml`

The PR creator and workflow smoke tests use invalid input deliberately. This verifies the hosted Responses endpoint without writing to a repository during deployment.

## Local deployment

Authenticate Azure CLI and azd, configure each agent project's azd environment with the existing project endpoint, create the `openapi-pr-github` connection, and deploy in dependency order:

```bash
cd agents/hosted/openapi-spec-pr-creator
azd deploy openapi-spec-pr-creator --no-prompt
```

Then deploy the orchestrator:

```bash
cd ../openapi-spec-workflow
azd deploy openapi-spec-workflow --no-prompt
```

No destination repository is fixed at deployment time. Supply it as `targetRepository` whenever the workflow is invoked.
