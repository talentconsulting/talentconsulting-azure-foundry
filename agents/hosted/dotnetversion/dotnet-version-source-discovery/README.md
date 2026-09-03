# .NET Version Source Discovery

Deterministically selects `.csproj` and `global.json` files beneath one public GitHub tree URL, ignoring `bin`, `obj`, `packages`, and `node_modules` directories. It returns bounded same-repository blob URLs and exclusions; no model is used.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src"}
```

```json
{"dotnetVersionFiles":["https://github.com/owner/repository/blob/main/src/App/App.csproj","https://github.com/owner/repository/blob/main/src/global.json"],"excludedFiles":[]}
```

```bash
python3 -m unittest discover -s src/dotnet-version-source-discovery -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy dotnet-version-source-discovery --no-prompt
```
