# Database Schema Source Discovery

Deterministically selects database DDL, migrations, ORM mappings, contexts, entities, and named types beneath one public GitHub tree URL. It returns `schemaFiles` as same-repository, same-ref GitHub blob URLs and reports safety-limit exclusions in `excludedFiles`. No model is used.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src/Database"}
```

Deploy with:

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy dbschema-source-discovery --no-prompt
```
