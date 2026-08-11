# Service Dependency Source Discovery

Deterministically selects files that evidence outbound HTTP API and gRPC dependencies beneath one public GitHub tree URL. It recognises API clients, client registrations, endpoint configuration keys, and protobuf services while excluding databases, messaging, caches, storage, and cloud-resource integrations. It returns bounded same-repository blob URLs and exclusions; no model is used.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src"}
```

```bash
python3 -m unittest discover -s src/service-dependency-source-discovery -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy service-dependency-source-discovery --no-prompt
```
