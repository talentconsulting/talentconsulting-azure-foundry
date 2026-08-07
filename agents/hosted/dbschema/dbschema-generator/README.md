# Database Schema Generator

A Python hosted agent that scans one public GitHub repository path for database entities, ORM mappings, migrations, DDL, and schema files, then returns one validated JSON representation of the database.

## Input

Direct calls use one credential-free GitHub tree URL:

```json
{
  "sourceUrl": "https://github.com/owner/repository/tree/main/src/Data"
}
```

The schema workflow may additionally supply a `sourceFiles` array of selected, same-repository GitHub blob URLs. This internal path is how discovery prevents an arbitrary archive subset from becoming the generator input.

The supplied path bounds discovery. The generator recognises database signals in C#, SQL, Prisma, Python, JavaScript/TypeScript, Java/Kotlin, Go, Ruby, PHP, and XML/YAML schema or migration files.

## Output

The response is the database representation itself, without Markdown or a wrapper:

```json
{
  "database": {
    "name": "catalog",
    "engine": "PostgreSQL"
  },
  "tables": [
    {
      "name": "orders",
      "schema": "public",
      "entity": "Order",
      "columns": [
        {
          "name": "id",
          "type": "uuid",
          "nullable": false,
          "primaryKey": true,
          "generated": true,
          "default": "gen_random_uuid()",
          "ordinal": 1
        }
      ],
      "relationships": [],
      "indexes": []
    }
  ],
  "types": []
}
```

Defaults are stored as SQL-expression strings; numeric and Boolean defaults are normalised to strings (for example, `0` becomes `"0"`). Unknown scalar values are `null`. The generator does not invent structures that are not evidenced by the selected source files.

## Safety and limits

- Repository archive: 100 MiB compressed, 250 MiB uncompressed
- Selected database files: at most 100
- Individual selected file: 512 KiB
- Combined selected source: 2 MiB
- Ignored paths include build outputs, dependencies, test projects, and ad-hoc maintenance scripts

Repository and source text are treated as untrusted data. The agent only accepts public, credential-free GitHub URLs.

## Test

```bash
python3 -m unittest discover -s src/dbschema-generator -p 'test_*.py'
```

## Local run

Create `src/dbschema-generator/.env` from `.env.example`, then run:

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent run dbschema-generator --no-client
```

In a second terminal:

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd ai agent invoke dbschema-generator --local \
  '{"sourceUrl":"https://github.com/owner/repository/tree/main/src/Data"}'
```

## Deploy

```bash
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy dbschema-generator --no-prompt
```

The root workflow `.github/workflows/deploy-dbschema-generator.agent.yml` runs unit tests, deploys the hosted agent, verifies its status, and performs an invalid-input Responses contract smoke test without reading GitHub or calling the model.
