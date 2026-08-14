# VBOOK-07 — Add idempotency and safe mutations

**Priority:** P0
**Goal:** Learn production API reliability patterns.

## Description

Make booking mutations safe when clients retry requests.

## TODO

* [ ] Add `Idempotency-Key` support
* [ ] Persist idempotency keys
* [ ] Store the original operation result
* [ ] Return the same result for duplicate calls
* [ ] Define expiration strategy
* [ ] Add tests simulating network retry
* [ ] Apply idempotency to:

  * create booking
  * cancel booking
  * reschedule booking

## Learning objectives

Understand why:

```text
request
→ mutation succeeds
→ response gets lost
→ request retries
```

must not create duplicate state.

## Acceptance criteria

Repeating an identical booking request with the same idempotency key never creates an additional booking.
