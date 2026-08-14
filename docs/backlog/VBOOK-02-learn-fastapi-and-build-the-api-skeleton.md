# VBOOK-02 — Learn FastAPI and build the API skeleton

**Priority:** P0
**Goal:** Become comfortable building typed REST APIs with FastAPI.

## Description

Build the first application endpoints without introducing database persistence yet.

## TODO

* [ ] Learn FastAPI routing
* [ ] Learn request/response Pydantic models
* [ ] Learn dependency injection with `Depends`
* [ ] Understand `async def` vs `def` FastAPI handlers
* [ ] Create API routers for:

  * businesses
  * services
  * employees
  * availability
  * bookings
* [ ] Implement temporary in-memory storage
* [ ] Add:

  * `GET /businesses`
  * `GET /businesses/{id}/services`
  * `GET /businesses/{id}/employees`
* [ ] Define consistent API error responses
* [ ] Explore generated OpenAPI documentation
* [ ] Call the endpoints manually using curl or HTTPie

## Learning objectives

Understand how FastAPI maps:

```text
HTTP request
    ↓
Pydantic validation
    ↓
route handler
    ↓
service
    ↓
response model
```

## Acceptance criteria

The API exposes working OpenAPI documentation and returns strongly typed responses.
