# Service Dependency Generator

Reads a bounded set of source files chosen by `service-dependency-source-discovery` and returns a validated catalog containing only outbound HTTP API and gRPC dependencies. It records configuration keys and source evidence but never returns secret values; databases, messaging, caches, storage, and cloud resources are excluded.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src","sourceFiles":["https://github.com/owner/repository/blob/main/src/Clients/AccountsClient.cs"]}
```

```bash
python3 -m unittest discover -s src/service-dependency-generator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy service-dependency-generator --no-prompt
```
