# VBOOK-06 — Implement transactional booking

**Priority:** P0
**Goal:** Learn database transactions and concurrency through a real problem.

## Description

Implement appointment creation while guaranteeing that two customers cannot reserve the same slot.

## TODO

* [ ] Add `POST /bookings`
* [ ] Validate customer
* [ ] Validate service
* [ ] Validate employee
* [ ] Validate requested slot
* [ ] Detect overlapping bookings
* [ ] Investigate PostgreSQL approaches for preventing conflicts
* [ ] Implement transaction boundaries
* [ ] Explore pessimistic locking with `SELECT ... FOR UPDATE`
* [ ] Understand database constraints as an alternative
* [ ] Simulate two concurrent booking requests
* [ ] Ensure exactly one succeeds
* [ ] Return a meaningful conflict error to the loser

## Learning objectives

Understand:

* transactions
* race conditions
* isolation
* locking
* consistency
* async concurrency

## Acceptance criteria

100 simultaneous attempts to reserve the same appointment result in **exactly one confirmed booking**.
