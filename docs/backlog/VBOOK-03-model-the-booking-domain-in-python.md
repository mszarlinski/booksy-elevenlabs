# VBOOK-03 — Model the booking domain in Python

**Priority:** P0
**Goal:** Practice Python domain modeling rather than putting all logic inside API handlers.

## Description

Model the minimum Booksy-like domain.

Initial entities:

```text
Business
Employee
Service
EmployeeService
Availability
Customer
Booking
```

## TODO

* [ ] Define domain entities
* [ ] Decide which models should be:

  * SQLAlchemy models
  * Pydantic DTOs
  * plain Python domain objects
* [ ] Model service duration
* [ ] Model service price
* [ ] Model employees capable of performing specific services
* [ ] Model business opening hours
* [ ] Model employee working hours
* [ ] Model booking status
* [ ] Add domain validation
* [ ] Seed one fictional Warsaw barber shop
* [ ] Seed 2–3 employees
* [ ] Seed 3–4 services

## Learning objectives

Practice:

* Python classes
* dataclasses where appropriate
* enums
* Pydantic models
* separation between transport and domain models
* Python typing

## Acceptance criteria

The domain can represent:

> Adam performs Men's Haircut for 100 PLN, lasting 45 minutes, and works Monday from 10:00–18:00.
