# Evaluations

## Evaluation 1: No Endpoints Found

### Input

{
  "repository": "org/example-api",
  "scanPath": "docs"
}

### Expected Behaviour

Return:

`{"specs":[]}`

## Evaluation 2: Multiple APIs In One Scan Path

### Source Pattern

```text
src/
  Orders/
    Controllers/OrdersController.cs
  Customers/
    Controllers/CustomersController.cs
  Invoices/
    Controllers/InvoicesController.cs
```

### Expected Behaviour

Return one top-level JSON object with a `specs` array containing one spec for each route-bearing source file: orders, customers, and invoices.

Each spec must include:

- `domain-api`
- `open-api`
- `serviceName`
- `sourcePath`
- `fileName`
- `contentType`

Each `open-api` must include:

- `openapi: 3.1.0`
- `info`
- `paths`
- `components.securitySchemes`
- `components.schemas`
- `security`

## Evaluation 3: All Endpoints Included

### Source Pattern

```text
OrdersController
  GET /api/orders
  POST /api/orders
  GET /api/orders/{orderId}
  PATCH /api/orders/{orderId}/status
  DELETE /api/orders/{orderId}
```

### Expected Behaviour

The returned OpenAPI object for the orders API includes all five paths/methods. It must not stop after the first endpoint or first few methods.

## Evaluation 3a: One Controller File Is Not The Whole Directory

### Source Pattern

```text
src/
  Orders/Controllers/OrdersController.cs
    GET /api/orders
    POST /api/orders
    GET /api/orders/{orderId}
  Orders/Controllers/OrderFilesController.cs
    GET /api/orders/{orderId}/files
    POST /api/orders/{orderId}/files
  Customers/Controllers/CustomersController.cs
    GET /api/customers
```

### Expected Behaviour

The response must include one spec for `OrdersController.cs`, one spec for `OrderFilesController.cs`, and one spec for `CustomersController.cs`.

It is invalid to return one spec whose `sourcePath` is only `src/Orders/Controllers/OrdersController.cs` and whose paths include only `/api/orders` endpoints.

## Evaluation 3b: ASP.NET Route Attributes Become OpenAPI Paths

### Source Pattern

```csharp
[ApiController]
[Route("api/[controller]")]
public class BidsController : ControllerBase
{
    [HttpGet]
    public IActionResult List() {}

    [HttpGet("{id:guid}")]
    public IActionResult Get(Guid id) {}

    [HttpPost]
    public IActionResult Create([FromBody] CreateBidRequest request) {}

    [HttpPatch("{id:guid}/status")]
    public IActionResult UpdateStatus(Guid id, [FromBody] UpdateBidStatusRequest request) {}
}
```

### Expected Behaviour

The returned OpenAPI paths must include:

- `GET /api/bids`
- `GET /api/bids/{id}`
- `POST /api/bids`
- `PATCH /api/bids/{id}/status`

The `{id:guid}` route constraint must be represented as an `{id}` path parameter with a string `uuid` schema where possible.

It is invalid to return `{"specs":[]}` or a spec with an empty `paths` object for this controller.

## Evaluation 3c: Multiple Controller Files In Same Domain

### Source Pattern

```text
src/Bids/Controllers/BidDocumentController.cs
src/Bids/Controllers/BidQuestionUserController.cs
src/Bids/Controllers/BidUserController.cs
src/Bids/Controllers/BidsController.cs
src/Bids/Controllers/ChatQuestionController.cs
src/Bids/Controllers/DraftResponseController.cs
src/Bids/Controllers/FinalAnswerController.cs
src/Bids/Controllers/RedReviewController.cs
src/Bids/Controllers/TasksController.cs
```

Each controller contains at least one public action with an ASP.NET Core HTTP method attribute.

### Expected Behaviour

The response must return one spec per controller file. With the nine controller files listed above, the `specs` array must contain nine items.

Each spec's `sourcePath` must be the repository-relative path of the controller file used to generate that spec.

It is invalid to include endpoints from only `BidsController.cs` or only the first controller file read.

It is invalid to return one grouped Bids API spec for all nine controller files.

It is also invalid to return only one otherwise-correct spec for `BidDocumentController.cs` when the other controller files listed above also contain HTTP action methods.

### Invalid Output Pattern

```json
{
  "specs": [
    {
      "domain-api": "bid-document-api",
      "open-api": {
        "openapi": "3.1.0",
        "info": {
          "title": "Bid Document API",
          "version": "3.1.0"
        },
        "paths": {
          "/api/document": {
            "post": {
              "responses": {
                "200": {
                  "description": "OK"
                }
              }
            }
          }
        },
        "components": {
          "securitySchemes": {},
          "schemas": {}
        },
        "security": []
      },
      "serviceName": "Bid Document API",
      "sourcePath": "src/Bids/Controllers/BidDocumentController.cs",
      "fileName": "bid-document-api.json",
      "contentType": "application/json"
    }
  ]
}
```

This output is invalid because the scan found multiple controller files with endpoints but returned only one spec.

## Evaluation 4: Existing OpenAPI Document

### Source Pattern

```text
src/openapi/orders.json
src/openapi/customers.json
```

### Expected Behaviour

Return one spec for each existing OpenAPI document. Preserve the OpenAPI path coverage and normalize to the required wrapper shape.

## Evaluation 4a: Specs Cannot Have Empty Paths

### Source Pattern

```text
src/Orders/Controllers/OrdersController.cs
src/Customers/Controllers/CustomersController.cs
```

### Invalid Output

```json
{
  "specs": [
    {
      "domain-api": "orders-api",
      "open-api": {
        "openapi": "3.1.0",
        "info": {
          "title": "Orders API",
          "version": "3.1.0"
        },
        "paths": {},
        "components": {
          "securitySchemes": {},
          "schemas": {}
        },
        "security": []
      },
      "serviceName": "Orders API",
      "sourcePath": "src/Orders",
      "fileName": "orders-api.json",
      "contentType": "application/json"
    }
  ]
}
```

### Expected Behaviour

Do not return any spec with an empty `paths` object. Extract endpoint paths from the API files. If no endpoint paths can be extracted, return `{"specs":[]}`.

## Evaluation 5: Infrastructure Endpoints

### Source Pattern

```text
src/Program.cs
GET /health
GET /
GET /swagger
src/Orders/Controllers/OrdersController.cs
GET /api/orders
```

### Expected Behaviour

Return a spec containing `/api/orders`. Do not return a health-only or root-redirect-only spec when application endpoints exist.

## Evaluation 5a: Program File Is Not Enough

### Source Pattern

```text
src/Program.cs
  GET /
  GET /health

src/Orders/Controllers/OrdersController.cs
  GET /api/orders
  POST /api/orders

src/Customers/Controllers/CustomersController.cs
  GET /api/customers
```

### Expected Behaviour

The response must include specs for the application endpoints in `OrdersController.cs` and `CustomersController.cs`. It must not return a spec containing only `/` and `/health`.

## Evaluation 6: Output Shape

### Expected Behaviour

The response must:

- Be valid JSON.
- Start with `{` and end with `}`.
- Have exactly one top-level property: `specs`.
- Return exactly one spec per discovered API endpoint source file.
- Return `open-api` as a JSON object, not a string.
- Never return a spec whose `open-api.paths` object is empty.
- Use `contentType: application/json`.
- Use `.json` filenames.
- Include no markdown or prose.
