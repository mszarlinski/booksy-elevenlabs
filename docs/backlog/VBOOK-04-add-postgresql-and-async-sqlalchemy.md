# VBOOK-04 — Add PostgreSQL and async SQLAlchemy

**Priority:** P0
**Goal:** Learn idiomatic database access in modern async Python.

## Description

Replace in-memory persistence with PostgreSQL.

## TODO

* [ ] Start PostgreSQL through Docker Compose
* [ ] Configure SQLAlchemy 2.x
* [ ] Use `asyncpg`
* [ ] Create `AsyncEngine`
* [ ] Create `AsyncSession`
* [ ] Understand Python async context managers
* [ ] Implement FastAPI database dependency
* [ ] Add SQLAlchemy mappings for domain entities
* [ ] Add Alembic
* [ ] Create the initial migration
* [ ] Add a seed script
* [ ] Implement basic repositories
* [ ] Practice SQLAlchemy:

  * `select`
  * joins
  * relationships
  * transactions

## Learning objectives

Pay particular attention to:

```python
async with session:
    ...
```

and:

```python
async with session.begin():
    ...
```

Understand what they actually do.

## Acceptance criteria

Restarting the service preserves businesses, employees, services, and bookings.
