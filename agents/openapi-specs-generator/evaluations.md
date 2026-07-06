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

The OpenAPI JSON object should contain:

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

The OpenAPI JSON object should contain:

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

The OpenAPI JSON object should include a security scheme when authentication can be identified.

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

## Evaluation 7: Explicit controller path inventory

### Input

```json
{
  "repository": "talentconsulting/talentsuite-bidmanager",
  "scanPath": "src/TalentSuite.Server",
  "controllerPaths": [
    "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
    "src/TalentSuite.Server/Bids/Controllers/BidDocumentController.cs",
    "src/TalentSuite.Server/Users/Controllers/UsersController.cs",
    "src/TalentSuite.Server/Users/Controllers/UserInvitesController.cs"
  ]
}
```

### Expected Behaviour

The response must read every supplied controller path and return one `specs` item for each routable controller. Each spec `sourcePath` must exactly match the controller path it was generated from. It must not return only `BidsController.cs` or only controllers from the `Bids/Controllers` folder.

## Evaluation 8: Complete action extraction within one controller

### Input

```json
{
  "repository": "talentconsulting/talentsuite-bidmanager",
  "scanPath": "src/TalentSuite.Server",
  "controllerPaths": [
    "src/TalentSuite.Server/Bids/Controllers/BidsController.cs"
  ],
  "controllerEndpoints": [
    {
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "controllerName": "BidsController",
      "actionName": "Create",
      "method": "post",
      "path": "/api/bids"
    },
    {
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "controllerName": "BidsController",
      "actionName": "Get",
      "method": "get",
      "path": "/api/bids/{bidId}"
    },
    {
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "controllerName": "BidsController",
      "actionName": "Get",
      "method": "get",
      "path": "/api/bids"
    },
    {
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "controllerName": "BidsController",
      "actionName": "SetStatus",
      "method": "patch",
      "path": "/api/bids/{bidId}/status"
    },
    {
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "controllerName": "BidsController",
      "actionName": "UpdateOverview",
      "method": "patch",
      "path": "/api/bids/{bidId}/overview"
    },
    {
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "controllerName": "BidsController",
      "actionName": "GetFiles",
      "method": "get",
      "path": "/api/bids/{bidId}/files"
    },
    {
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "controllerName": "BidsController",
      "actionName": "UploadFile",
      "method": "post",
      "path": "/api/bids/{bidId}/files"
    },
    {
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "controllerName": "BidsController",
      "actionName": "DownloadFile",
      "method": "get",
      "path": "/api/bids/{bidId}/files/{fileId}"
    },
    {
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "controllerName": "BidsController",
      "actionName": "DeleteFile",
      "method": "delete",
      "path": "/api/bids/{bidId}/files/{fileId}"
    },
    {
      "sourcePath": "src/TalentSuite.Server/Bids/Controllers/BidsController.cs",
      "controllerName": "BidsController",
      "actionName": "PushToBidLibrary",
      "method": "post",
      "path": "/api/bids/{bidId}/library-push"
    }
  ]
}
```

### Expected Behaviour

The returned spec for `BidsController.cs` must contain all 10 supplied endpoints. It must not stop after `Create`, `Get`, and `SetStatus`. It must include later action methods such as `UpdateOverview`, `GetFiles`, `UploadFile`, `DownloadFile`, `DeleteFile`, and `PushToBidLibrary`.

## Evaluation Checks

The response must:

- Be valid JSON.
- Start with `{` and end with `}` without markdown code fences or explanatory text.
- Match the configured schema.
- Include `domain-api`.
- Include `open-api`.
- Include `fileName`.
- Include `contentType` as `application/json`.
- Return `open-api` as a JSON object, not a string.
- Set `sourcePath` to the controller file path used to generate the spec.
- Contain valid OpenAPI JSON.
- Contain no markdown outside the JSON response.
- Contain no additional JSON properties.
