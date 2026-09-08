# Repository Metadata Source Discovery

Deterministically selects `.csproj`, `global.json`, `.bicep`, and `.tf` files beneath one public GitHub tree URL, ignoring `bin`, `obj`, `packages`, `node_modules`, and `.terraform` (Terraform's local provider/module cache) directories. It returns bounded same-repository blob URLs and exclusions; no model is used.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src"}
```

```json
{"repoMetadataFiles":["https://github.com/owner/repository/blob/main/src/App/App.csproj","https://github.com/owner/repository/blob/main/src/global.json","https://github.com/owner/repository/blob/main/src/infra/main.bicep"],"excludedFiles":[]}
```

```bash
python3 -m unittest discover -s src/repo-metadata-source-discovery -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy repo-metadata-source-discovery --no-prompt
```
