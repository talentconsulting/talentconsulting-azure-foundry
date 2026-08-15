# C4 Generator

Reads a bounded set of files chosen by `c4-source-discovery` and returns validated C4 context and container diagrams. The response contains canonical `c4Model` JSON plus draw.io `mxfile` XML for `context.drawio` and `container.drawio`.

```json
{"sourceUrl":"https://github.com/owner/repository/tree/main/src","sourceFiles":["https://github.com/owner/repository/blob/main/src/Program.cs"]}
```

```bash
python3 -m unittest discover -s src/c4-generator -p 'test_*.py'
AZURE_DEV_USER_AGENT=microsoft_foundry_skill azd deploy c4-generator --no-prompt
```
