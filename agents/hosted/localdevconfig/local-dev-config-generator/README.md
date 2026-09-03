# Local Dev Config Generator

A Python hosted agent that reads a bounded set of source files selected from one GitHub repository and returns one validated JSON catalog of the local services (databases, caches, message brokers, object storage) and configuration key names a developer needs to run that repository locally. It records configuration key names and source evidence but never returns secret values.

## Input

Both fields are required: a credential-free GitHub tree URL and the array of same-repository, same-ref GitHub blob URLs to read.

```json
{
  "sourceUrl": "https://github.com/owner/repository/tree/main/src",
  "sourceFiles": [
    "https://github.com/owner/repository/blob/main/src/docker-compose.yml",
    "https://github.com/owner/repository/blob/main/src/appsettings.json"
  ]
}
```

`sourceFiles` must contain between 1 and 100 entries, each a blob URL from `sourceUrl`'s owner, repository, and ref, with no duplicates.

## Output

The response is the catalog itself, without Markdown or a wrapper:

```json
{
  "repository": "owner/repository",
  "ref": "main",
  "path": "src",
  "localServices": [
    {
      "name": "Redis",
      "kind": "cache",
      "technology": "redis",
      "configurationKeys": ["ConnectionStrings:Redis"],
      "evidence": [
        {"sourceFile": "src/appsettings.json", "reason": "ConnectionStrings:Redis configured; AddStackExchangeRedisCache registered in Startup.cs"}
      ]
    }
  ],
  "configurationKeys": [
    {"key": "ConnectionStrings:Redis", "sourceFile": "src/appsettings.json", "reason": "Redis connection string entry"},
    {"key": "ConnectionStrings:Redis", "sourceFile": "src/.env.example", "reason": "Same key documented for local override"}
  ]
}
```

`kind` is one of `cache`, `database`, `message-broker`, `object-storage`, or `other`. `technology` is a short lowercase product slug (for example `redis`, `postgresql`, `azurite`) and may be `null` when no specific product is evidenced. A repository that needs no local services returns empty `localServices` and `configurationKeys` arrays -- that is a valid, not an erroneous, result.

Every top-level `configurationKeys[].key` is a plain key name: the generator rejects any key containing a URL scheme (`://`) or whitespace, since that would indicate a value leaked into the key position rather than a key name. Every `localServices[].configurationKeys` entry must also appear as a top-level `configurationKeys[].key`.

## Safety and limits

- Selected source files: at most 100
- Individual selected file: 512 KiB
- Combined selected source: 2 MiB

Source text is treated as untrusted data. The agent only accepts public, credential-free GitHub blob URLs from the same repository and ref as `sourceUrl`, and never returns credentials, tokens, connection-string values, or literal endpoint hostnames -- only configuration key names and source evidence.

## Test

```bash
python3 -m unittest discover -s src/local-dev-config-generator -p 'test_*.py'
```

## Local run

Create `src/local-dev-config-generator/.env` from `.env.example`, then run:

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent run local-dev-config-generator --no-client
```

In a second terminal:

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent invoke local-dev-config-generator --local \
  '{"sourceUrl":"https://github.com/owner/repository/tree/main/src","sourceFiles":["https://github.com/owner/repository/blob/main/src/docker-compose.yml"]}'
```

## Deploy

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy local-dev-config-generator --no-prompt
```
