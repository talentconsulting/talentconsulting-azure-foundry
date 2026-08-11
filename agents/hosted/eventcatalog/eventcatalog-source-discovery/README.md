# Event and Command Catalog Source Discovery

Deterministically selects event, command, and handler source files beneath one public GitHub tree URL. It recognises common message names, folders, MediatR interfaces, message interfaces, and handler declarations. The response contains same-repository, same-ref `sourceFiles` plus bounded safety exclusions; no model is used.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src/Application"}
```

```bash
python3 -m unittest discover -s src/eventcatalog-source-discovery -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy eventcatalog-source-discovery --no-prompt
```
