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
app.MapOrderEndpoints();
```

### Expected Behaviour

Return `{"specs":[]}` when no controller classes are present. Do not generate specs from Minimal API route registrations.

## Evaluation 6: Multiple controllers in one server project

### Source Pattern

```text
src/My.Api/
  Orders/Controllers/OrdersController.cs
  Customers/Controllers/CustomersController.cs
  Invoices/Controllers/InvoicesController.cs
  Auth/Controllers/AuthController.cs
```

### Expected Behaviour

The response should contain separate `specs` items for the orders, customers, invoices, and auth controllers. It must not stop after the first `Controllers` directory; it must continue scanning sibling domain folders. It must not return a single generic repository-level spec when multiple controllers are present.

## Evaluation 7: Explicit controller path inventory

### Input

```json
{
  "repository": "example/example-api",
  "scanPath": "src/My.Api",
  "controllerPaths": [
    "src/My.Api/Orders/Controllers/OrdersController.cs",
    "src/My.Api/Orders/Controllers/OrderDocumentsController.cs",
    "src/My.Api/Customers/Controllers/CustomersController.cs",
    "src/My.Api/Invoices/Controllers/InvoicesController.cs"
  ]
}
```

### Expected Behaviour

The response must read every supplied controller path and return one `specs` item for each routable controller. Each spec `sourcePath` must exactly match the controller path it was generated from. It must not return only the first controller or only controllers from the first feature folder.

## Evaluation 8: Complete action extraction within one controller

### Input

```json
{
  "repository": "example/example-api",
  "scanPath": "src/My.Api",
  "controllerPaths": [
    "src/My.Api/Orders/Controllers/OrdersController.cs"
  ],
  "controllerEndpoints": [
    {
      "sourcePath": "src/My.Api/Orders/Controllers/OrdersController.cs",
      "controllerName": "OrdersController",
      "actionName": "Create",
      "method": "post",
      "path": "/api/orders"
    },
    {
      "sourcePath": "src/My.Api/Orders/Controllers/OrdersController.cs",
      "controllerName": "OrdersController",
      "actionName": "Get",
      "method": "get",
      "path": "/api/orders/{orderId}"
    },
    {
      "sourcePath": "src/My.Api/Orders/Controllers/OrdersController.cs",
      "controllerName": "OrdersController",
      "actionName": "Search",
      "method": "get",
      "path": "/api/orders"
    },
    {
      "sourcePath": "src/My.Api/Orders/Controllers/OrdersController.cs",
      "controllerName": "OrdersController",
      "actionName": "SetStatus",
      "method": "patch",
      "path": "/api/orders/{orderId}/status"
    },
    {
      "sourcePath": "src/My.Api/Orders/Controllers/OrdersController.cs",
      "controllerName": "OrdersController",
      "actionName": "UpdateDetails",
      "method": "patch",
      "path": "/api/orders/{orderId}/details"
    },
    {
      "sourcePath": "src/My.Api/Orders/Controllers/OrdersController.cs",
      "controllerName": "OrdersController",
      "actionName": "GetDocuments",
      "method": "get",
      "path": "/api/orders/{orderId}/documents"
    },
    {
      "sourcePath": "src/My.Api/Orders/Controllers/OrdersController.cs",
      "controllerName": "OrdersController",
      "actionName": "UploadDocument",
      "method": "post",
      "path": "/api/orders/{orderId}/documents"
    },
    {
      "sourcePath": "src/My.Api/Orders/Controllers/OrdersController.cs",
      "controllerName": "OrdersController",
      "actionName": "DownloadDocument",
      "method": "get",
      "path": "/api/orders/{orderId}/documents/{documentId}"
    },
    {
      "sourcePath": "src/My.Api/Orders/Controllers/OrdersController.cs",
      "controllerName": "OrdersController",
      "actionName": "DeleteDocument",
      "method": "delete",
      "path": "/api/orders/{orderId}/documents/{documentId}"
    },
    {
      "sourcePath": "src/My.Api/Orders/Controllers/OrdersController.cs",
      "controllerName": "OrdersController",
      "actionName": "Submit",
      "method": "post",
      "path": "/api/orders/{orderId}/submit"
    }
  ]
}
```

### Expected Behaviour

The returned spec for `OrdersController.cs` must contain all 10 supplied endpoints. It must not stop after `Create`, `Get`, and `SetStatus`. It must include later action methods such as `UpdateDetails`, `GetDocuments`, `UploadDocument`, `DownloadDocument`, `DeleteDocument`, and `Submit`.

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
