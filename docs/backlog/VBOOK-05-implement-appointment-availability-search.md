# VBOOK-05 — Implement appointment availability search

**Priority:** P0
**Goal:** Implement the first meaningful piece of business logic.

## Description

Given a service, date/time constraints, and optionally an employee, calculate available appointment slots.

Example query:

> Men's haircut tomorrow after 17:00.

## TODO

* [ ] Implement employee working hours
* [ ] Calculate possible slots based on service duration
* [ ] Remove slots overlapping existing bookings
* [ ] Add optional employee filtering
* [ ] Add time-range filtering
* [ ] Add price filtering
* [ ] Expose:

```http
GET /availability
```

* [ ] Support parameters such as:

  * service
  * employee
  * date
  * earliest time
  * latest time
* [ ] Return a stable machine-friendly structure
* [ ] Add unit tests for slot calculations
* [ ] Test boundary conditions

## Learning objectives

Practice:

* `datetime`
* timezone handling
* collections
* comprehensions
* sorting/filtering
* domain services
* unit testing

## Acceptance criteria

The backend can answer:

> Find all haircut appointments tomorrow between 17:00 and 20:00.
