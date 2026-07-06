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

Return one top-level JSON object with a `specs` array containing separate specs for orders, customers, and invoices.

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

## Evaluation 4: Existing OpenAPI Document

### Source Pattern

```text
src/openapi/orders.json
src/openapi/customers.json
```

### Expected Behaviour

Return one spec for each existing OpenAPI document. Preserve the OpenAPI path coverage and normalize to the required wrapper shape.

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
- Return `open-api` as a JSON object, not a string.
- Use `contentType: application/json`.
- Use `.json` filenames.
- Include no markdown or prose.
