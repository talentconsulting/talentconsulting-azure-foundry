# Evaluations

## Evaluation 1: No endpoints found

### Input

```json
{
  "repository": "TalentConsulting/example-api",
  "scanPath": "docs",
  "openApiTitle": "Example API"
}
```

### Expected Behaviour

Return a valid OpenAPI 3.1.0 YAML document with an empty `paths` object.

## Evaluation 2: Single GET endpoint

### Source Pattern

```csharp
[HttpGet("{id}")]
public async Task<ActionResult<AccountResponse>> GetAccount(Guid id)
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
[HttpPost]
public async Task<ActionResult<CreateAccountResponse>> CreateAccount(CreateAccountRequest request)
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
[Authorize]
[HttpGet]
public IActionResult GetSecureResource()
```

### Expected Behaviour

The YAML should include a security scheme when authentication can be identified.

## Evaluation 5: Minimal API endpoints in extension methods

### Source Pattern

```csharp
app.MapGet("/", () => Results.Redirect("/health"));
app.MapGet("/health", () => Results.Ok());
app.MapBidEndpoints();

public static class BidEndpoints
{
    public static IEndpointRouteBuilder MapBidEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/bids");
        group.MapGet("/", GetBids);
        group.MapGet("/{id}", GetBid);
        group.MapPost("/", CreateBid);
        return app;
    }
}
```

### Expected Behaviour

The YAML must include `/api/bids`, `/api/bids/{id}`, and their HTTP methods. It must not return only `/` and `/health`.

## Evaluation Checks

The response must:

- Be valid JSON.
- Match the configured schema.
- Include `domain-api`.
- Include `open-api`.
- Include `fileName`.
- Include `contentType` as `application/yaml`.
- Contain valid OpenAPI YAML.
- Contain no markdown outside the JSON response.
- Contain no additional JSON properties.
