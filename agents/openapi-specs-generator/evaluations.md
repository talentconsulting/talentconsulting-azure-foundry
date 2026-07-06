# Evaluations

## Evaluation 1: No controllers found

### Input

```json
{
  "repository": "TalentConsulting/example-api",
  "scanPath": "docs"
}
```

### Expected Behaviour

Return valid schema JSON with an empty `specs` array.

## Evaluation 2: Single GET endpoint

### Source Pattern

```csharp
[ApiController]
[Route("api/accounts")]
public class AccountsController : ControllerBase
{
[HttpGet("{id}")]
public async Task<ActionResult<AccountResponse>> GetAccount(Guid id)
}
```

### Expected Behaviour

The YAML should contain:

- `openapi: 3.1.0`
- A path containing `{id}`
- A `get` operation
- A path parameter named `id`
- A `200` response
- A schema for `AccountResponse` where possible

## Evaluation 3: POST endpoint with request body

### Source Pattern

```csharp
[ApiController]
[Route("api/accounts")]
public class AccountsController : ControllerBase
{
[HttpPost]
public async Task<ActionResult<CreateAccountResponse>> CreateAccount(CreateAccountRequest request)
}
```

### Expected Behaviour

The YAML should contain:

- A `post` operation
- A `requestBody`
- A `201` or `200` response depending on source code hints
- Components for request and response schemas where possible

## Evaluation 4: Authenticated endpoint

### Source Pattern

```csharp
[ApiController]
[Route("api/secure")]
public class SecureController : ControllerBase
{
[Authorize]
[HttpGet]
public IActionResult GetSecureResource()
}
```

### Expected Behaviour

The YAML should include a security scheme when authentication can be identified.

## Evaluation 5: Ignore Minimal API endpoints

### Source Pattern

```csharp
app.MapGet("/", () => Results.Redirect("/health"));
app.MapGet("/health", () => Results.Ok());
app.MapBidEndpoints();
```

### Expected Behaviour

Return `{"specs":[]}` when no controller classes are present. Do not generate specs from Minimal API route registrations.

## Evaluation 6: Multiple controllers in one server project

### Source Pattern

```text
src/TalentSuite.Server/
  Bids/Controllers/BidsController.cs
  Users/Controllers/UsersController.cs
  Messages/Controllers/MessagesController.cs
  Auth/Controllers/AuthController.cs
```

### Expected Behaviour

The response should contain separate `specs` items for the bids, users, messages, and auth controllers. It must not stop after `Bids/Controllers`; it must continue scanning sibling domain folders such as `Users/Controllers`. It must not return a single generic `talentsuite-api` spec when multiple controllers are present.

## Evaluation Checks

The response must:

- Be valid JSON.
- Start with `{` and end with `}` without markdown code fences or explanatory text.
- Match the configured schema.
- Include `domain-api`.
- Include `open-api`.
- Include `fileName`.
- Include `contentType` as `application/yaml`.
- Contain valid OpenAPI YAML.
- Contain no markdown outside the JSON response.
- Contain no additional JSON properties.
