# Local Dev Config Source Discovery

Deterministically selects files that evidence the local services (databases, caches, message brokers, object storage) and configuration key names a developer needs to run one repository locally, beneath one public GitHub tree URL. It always includes Docker Compose files, recognised application-config filenames, and `.env.example`/`.env.sample`/`.env.template` files on filename alone; when no Docker Compose file is present it also includes source files that construct or register a cache, database, message-broker, or object-storage client. It returns bounded same-repository blob URLs and exclusions; no model is used.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src"}
```

```json
{"localDevConfigFiles":["https://github.com/owner/repository/blob/main/src/docker-compose.yml","https://github.com/owner/repository/blob/main/src/appsettings.json"],"excludedFiles":[]}
```

```bash
python3 -m unittest discover -s src/local-dev-config-source-discovery -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy local-dev-config-source-discovery --no-prompt
```
