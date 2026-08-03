# Evaluations

## Evaluation 1: Valid Minimal Spec

### Input

An OpenAPI 3.1 document with `openapi`, `info`, and an empty `paths` object.

### Expected Behaviour

Return `valid: true`, `severity: none`, `recommendedAction: accept`, and no findings.

## Evaluation 2: Missing Paths

### Input

An OpenAPI document with no `paths` object.

### Expected Behaviour

Return `valid: false`, include a high severity finding, and set `recommendedAction` to `regenerate`.

## Evaluation 3: Missing Operation Responses

### Input

An operation with no `responses` block.

### Expected Behaviour

Return a finding describing the missing responses and recommend review or regeneration depending on severity.

## Evaluation Checks

The response must:

- Be valid JSON.
- Match the configured schema.
- Include `domain-api`.
- Include `fileName`.
- Include `valid`.
- Include `severity`.
- Include `recommendedAction`.
- Include `summary`.
- Include `findings`.
- Contain no markdown outside the JSON response.
- Contain no additional JSON properties.
