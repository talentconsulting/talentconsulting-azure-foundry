# Evaluations

## Evaluation 1: Empty manifest

### Input

```json
{
  "manifestRepository": "TalentConsulting/DomainExplorer",
  "manifestPath": "repoManifest.json"
}
```

### Manifest State

The manifest contains no repositories.

### Expected Output

```json
{
  "repositories": []
}
```

## Evaluation 2: Repository latestCommit is null

### Manifest Entry

```json
{
  "repoName": "example-api",
  "repoURL": "https://github.com/TalentConsulting/example-api",
  "latestCommit": null
}
```

### Expected Output

```json
{
  "repositories": [
    {
      "repoName": "example-api",
      "repoURL": "https://github.com/TalentConsulting/example-api",
      "repository": "TalentConsulting/example-api"
    }
  ]
}
```

## Evaluation 3: Repository latestCommit matches GitHub

### Manifest Entry

```json
{
  "repoName": "example-api",
  "repoURL": "https://github.com/TalentConsulting/example-api",
  "latestCommit": "abc123"
}
```

### Live GitHub Latest Commit

```text
abc123
```

### Expected Output

```json
{
  "repositories": []
}
```

## Evaluation 4: Repository latestCommit differs from GitHub

### Manifest Entry

```json
{
  "repoName": "example-api",
  "repoURL": "https://github.com/TalentConsulting/example-api",
  "latestCommit": "abc123"
}
```

### Live GitHub Latest Commit

```text
def456
```

### Expected Output

```json
{
  "repositories": [
    {
      "repoName": "example-api",
      "repoURL": "https://github.com/TalentConsulting/example-api",
      "repository": "TalentConsulting/example-api"
    }
  ]
}
```

## Evaluation 5: Invalid or inaccessible repository

### Manifest Entry

```json
{
  "repoName": "missing-api",
  "repoURL": "https://github.com/TalentConsulting/missing-api",
  "latestCommit": "abc123"
}
```

### Expected Output

```json
{
  "repositories": [
    {
      "repoName": "missing-api",
      "repoURL": "https://github.com/TalentConsulting/missing-api",
      "repository": "TalentConsulting/missing-api"
    }
  ]
}
```

## Evaluation Checks

The response must:

- Be valid JSON.
- Match the configured schema.
- Contain no markdown.
- Contain no additional properties.
- Always include the top-level `repositories` property.
