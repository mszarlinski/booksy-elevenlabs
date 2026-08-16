# VBOOK-06 — Implement transactional booking — Design

**Story:** [VBOOK-06](../../backlog/VBOOK-06-implement-transactional-booking.md)
**Depends on:** [VBOOK-04's design](2026-08-16-vbook-04-postgresql-async-sqlalchemy-design.md) — this ticket only makes sense once bookings live in Postgres behind the `SqlAlchemyBookingRepository` adapter VBOOK-04 introduces.

## Context

Today, `POST /bookings` takes a free-text `service: str` (never validated against
anything) and an optional `employee_id`, and creates a booking with zero conflict
checking — two customers can book the exact same employee at the exact same time, or at
overlapping times, and both succeed. This ticket makes booking creation actually safe:
real validation, real overlap detection, and a locking strategy that holds under
concurrent requests.

Two things fall out of that goal and are addressed here even though they read as
schema/API changes rather than "transactional" work:

1. **`service` becomes `service_id` (required, validated).** A free-text string can't be
   used to look up a duration, and duration is required to know a booking's end time —
   which is required to detect overlaps at all. This isn't optional cleanup; overlap
   detection is impossible without it.
2. **`employee_id` becomes required.** Conflict prevention needs a specific employee row
   to lock and check overlaps against. A booking with no employee can't be protected
   from double-booking, so allowing it would leave a loophole that defeats the point of
   this ticket. `scripts/create_elevenlabs_agent.py`'s registered `create_booking` tool
   is updated to match (Section "ElevenLabs agent script" below), since VBOOK-10 already
   registered it with `employee_id` optional.

## Request/response schema change

`app/routers/bookings.py`'s `CreateBookingRequest` changes from:

```python
class CreateBookingRequest(BaseModel):
    customer_name: str
    service: str
    slot: str
    confirmed: bool
    employee_id: str | None = None
```

to:

```python
class CreateBookingRequest(BaseModel):
    customer_name: str
    service_id: str
    employee_id: str
    slot: str
    confirmed: bool
```

`app/adapters/db/models.py`'s `Booking` changes from `service: Mapped[str]` to
`service_id: Mapped[str] = mapped_column(ForeignKey("services.id"))`, and
`employee_id: Mapped[str | None]` (nullable) to `employee_id: Mapped[str] =
mapped_column(ForeignKey("employees.id"))` (not nullable). The dict shape returned by
every booking-repository method changes accordingly: `service` → `service_id` in
`GET /bookings`, `GET /bookings/{id}`, and the `POST /bookings` response.

## Domain exceptions (the port's real contract)

Four plain Python exceptions, defined in `app/repositories/bookings.py` alongside the
`BookingRepository` protocol — no SQLAlchemy import, so routers importing them stay
database-agnostic:

```python
class UnknownServiceError(Exception):
    pass


class UnknownEmployeeError(Exception):
    pass


class EmployeeCannotPerformServiceError(Exception):
    pass


class SlotConflictError(Exception):
    pass
```

A malformed `slot` string reuses the builtin `ValueError`, matching the existing
convention in `app/slots.py`. Together with these four, the adapter's `add` method never
lets a SQLAlchemy exception type (`IntegrityError`, etc.) escape to its caller.

## The transactional core

`SqlAlchemyBookingRepository.add` (`app/adapters/db/bookings.py`) does everything —
validation, locking, overlap detection, and the insert — inside one
`async with session.begin():` block. It has to: the employee-row lock only provides its
correctness guarantee if the overlap check and the insert happen in the same transaction
as the lock acquisition. Splitting reads into the router (as other endpoints do) and
only writing in the adapter would mean the "read" happens outside the lock, defeating
the whole point.

```python
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.models import Booking, Employee, Service
from app.adapters.db.session import get_session
from app.repositories.bookings import (
    EmployeeCannotPerformServiceError,
    SlotConflictError,
    UnknownEmployeeError,
    UnknownServiceError,
)


def _to_dict(booking: Booking) -> dict[str, str | None]:
    return {
        "id": booking.id,
        "customer_name": booking.customer_name,
        "service_id": booking.service_id,
        "employee_id": booking.employee_id,
        "slot": booking.slot,
        "status": booking.status,
    }


def _parse_slot(slot: str) -> datetime:
    try:
        return datetime.fromisoformat(slot)
    except ValueError as exc:
        raise ValueError(f"invalid slot: {slot!r}, expected YYYY-MM-DDTHH:MM") from exc


class SqlAlchemyBookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self, customer_name: str, service_id: str, employee_id: str, slot: str
    ) -> dict[str, str | None]:
        new_start = _parse_slot(slot)

        async with self._session.begin():
            employee_result = await self._session.execute(
                select(Employee)
                .options(selectinload(Employee.services))
                .where(Employee.id == employee_id)
                .with_for_update()
            )
            employee = employee_result.scalar_one_or_none()
            if employee is None:
                raise UnknownEmployeeError(employee_id)

            service = await self._session.get(Service, service_id)
            if service is None:
                raise UnknownServiceError(service_id)

            if service not in employee.services:
                raise EmployeeCannotPerformServiceError(employee_id, service_id)

            new_end = new_start + timedelta(minutes=service.duration_minutes)

            existing = await self._session.execute(
                select(Booking, Service.duration_minutes)
                .join(Service, Service.id == Booking.service_id)
                .where(Booking.employee_id == employee_id, Booking.status == "confirmed")
            )
            for other_booking, other_duration in existing:
                other_start = datetime.fromisoformat(other_booking.slot)
                other_end = other_start + timedelta(minutes=other_duration)
                if new_start < other_end and other_start < new_end:
                    raise SlotConflictError(employee_id, slot)

            booking = Booking(
                id=str(uuid4()),
                customer_name=customer_name,
                service_id=service_id,
                employee_id=employee_id,
                slot=slot,
                status="confirmed",
            )
            self._session.add(booking)

        return _to_dict(booking)


def get_booking_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyBookingRepository:
    return SqlAlchemyBookingRepository(session)
```

`.with_for_update()` locks the `employees` row for `employee_id` until the transaction
commits or rolls back — every concurrent `add()` call for the same employee serializes
on this line. Because the lock is on a row that always exists (the employee), this
works correctly even for a slot nobody has ever booked before — the classic gap in a
"lock the thing you're about to insert" approach, since there's nothing to lock yet.
`selectinload(Employee.services)` is a separate, unlocked query (it only needs to read
which services the employee performs, not protect against a race on that data) — the
`in` check against `employee.services` works because SQLAlchemy's per-session identity
map guarantees `service` (loaded via `session.get`) and the members of
`employee.services` are the same Python objects when they refer to the same row.

A partial unique index is added as a defense-in-depth backstop (see "Migration" below)
— the lock should make it unreachable in normal operation, but a future direct-SQL path
that bypasses this adapter would still be caught by the database itself.

## Router

`app/routers/bookings.py`'s `create_booking` handler stays thin — it maps each domain
exception to a status code and never touches SQLAlchemy:

```python
@router.post("/bookings")
async def create_booking(
    body: CreateBookingRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    repository: BookingRepository = Depends(get_booking_repository),
    idempotency: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> dict[str, str | None]:
    logger.info(
        "tool_request tool=create_booking service_id=%s slot=%s employee_id=%s confirmed=%s",
        body.service_id,
        body.slot,
        body.employee_id,
        body.confirmed,
    )
    if not body.confirmed:
        raise HTTPException(
            status_code=400,
            detail="booking must be explicitly confirmed by the customer before creation",
        )

    async def mutate() -> dict[str, str | None]:
        return await repository.add(body.customer_name, body.service_id, body.employee_id, body.slot)

    try:
        booking = await maybe_idempotent(idempotency_key, idempotency, mutate)
    except UnknownServiceError:
        raise HTTPException(status_code=404, detail=f"unknown service_id: {body.service_id}")
    except UnknownEmployeeError:
        raise HTTPException(status_code=404, detail=f"unknown employee_id: {body.employee_id}")
    except EmployeeCannotPerformServiceError:
        raise HTTPException(
            status_code=400,
            detail=f"employee {body.employee_id} does not perform service {body.service_id}",
        )
    except SlotConflictError:
        raise HTTPException(
            status_code=409,
            detail=f"employee {body.employee_id} already has a booking overlapping {body.slot}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info("tool_response tool=create_booking booking_id=%s", booking["id"])
    return booking
```

Note that a failed `mutate()` is never cached by `maybe_idempotent`/`get_or_create` —
looking at its implementation (from VBOOK-04), the result is only stored in
`self._entries` *after* `await compute()` returns successfully. A retried request that
previously got a `409`/`404`/`400` re-runs the full check on retry rather than replaying
a cached failure, which is the correct behavior for an idempotency key (it dedupes
successful mutations, not errors).

## Migration

One Alembic migration:
- Drop `bookings.service`.
- Add `bookings.service_id` (`ForeignKey("services.id")`, not null).
- Alter `bookings.employee_id` to not null.
- Add a partial unique index:

```python
Index(
    "uq_bookings_employee_slot_confirmed",
    "employee_id",
    "slot",
    unique=True,
    postgresql_where=text("status = 'confirmed'"),
)
```

in `Booking.__table_args__`, autogenerated as a `CREATE UNIQUE INDEX ... WHERE status =
'confirmed'` migration step.

This is a dev-only database with no production data — if the local `bookings` table
already has rows without a `service_id` or with a null `employee_id`, they violate the
new constraints. The plan will call for truncating `bookings` before running this
migration rather than writing backfill logic, since there's nothing meaningful to
backfill `service_id` from (the old `service` column is free text, not a real
reference).

## ElevenLabs agent script

`scripts/create_elevenlabs_agent.py`'s `create_booking` tool definition changes:
- `body_params`: `service` → `service_id` (description updated to say "use the
  `service_id` returned by `search_services`, not a name").
- `required_body_params`: adds `employee_id` (was optional).
- System prompt: the existing "Use search_employees if the customer asks for a specific
  staff member" line is replaced with wording that makes resolving a specific employee
  mandatory before booking (e.g., from `search_available_slots`' per-employee results),
  since `employee_id` is no longer optional at the API level.

Re-running this script against the real ElevenLabs account (updating the already-created
agent's registered tool) is a manual step for later — not run in this session, same as
VBOOK-09's original agent-creation script.

## Testing

No concurrency simulation in the automated suite — multi-threaded/concurrent-execution
tests are dropped from this project's test suite entirely (this generalizes a decision
already applied to `tests/test_idempotency.py` in VBOOK-04's plan). The row lock's
concurrency guarantee is a property of Postgres's `SELECT ... FOR UPDATE` semantics, not
something this codebase needs to re-demonstrate under pytest; it's verified manually
(e.g. firing several `curl -X POST` requests at a running instance in parallel) rather
than automated.

What *is* covered by deterministic, non-concurrent tests in `tests/test_bookings.py`:
- Two sequential requests for the same employee with overlapping times (not necessarily
  identical — e.g. a 45-minute service at 10:00 and a request for 10:30): first returns
  `200`, second returns `409`.
- Unknown `service_id` → `404`. Unknown `employee_id` → `404`.
- An employee who doesn't perform the requested service → `400`.
- Malformed `slot` → `400`.
- Two non-overlapping bookings for the same employee both succeed.
- A booking for a *different* employee at the exact same time as an existing one
  succeeds (proves the lock/check is scoped per-employee, not global).

## Out of scope

- A GiST exclusion constraint expressing overlap directly in the database (considered
  and rejected in favor of the app-level check + row lock, which is simpler and was
  explicitly requested).
- Advisory locks (`pg_advisory_xact_lock`) — considered and rejected in favor of locking
  the employee row directly.
- VBOOK-15's booking-hold flow (`hold_booking`/`confirm_booking`) — a separate, later
  ticket; this one keeps the single-step `create_booking` tool, just made safe.
- Any automated concurrency/multi-threaded test in pytest.
- Backfilling pre-existing booking rows during the migration — there are none worth
  preserving in this dev-only database.
- Validating `customer_name` beyond what `str` already requires (non-empty in the sense
  Pydantic enforces) — there's no customer entity in this domain to validate against.
