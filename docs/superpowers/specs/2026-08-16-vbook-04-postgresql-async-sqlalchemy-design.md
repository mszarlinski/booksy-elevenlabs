# VBOOK-04 — Add PostgreSQL and async SQLAlchemy — Design

**Story:** [VBOOK-04](../../backlog/VBOOK-04-add-postgresql-and-async-sqlalchemy.md)

## Context

Every repository today (`InMemoryBusinessRepository`, `InMemoryEmployeeRepository`,
`InMemoryServiceRepository`, `InMemoryBookingRepository`) is a module-level singleton
holding Python lists of dicts — data is lost on every restart. VBOOK-04 replaces this
with real PostgreSQL persistence via async SQLAlchemy 2.x, while keeping the existing
`InMemory*Repository` → `SqlAlchemy*Repository` swap as close to a drop-in replacement
as possible: same class names, same constructor-injected-per-request shape, same
dict-returning methods, so routers change minimally (add `async`/`await`) and existing
response shapes are untouched.

VBOOK-06 (transactional booking, detecting overlaps, locking) is **not** part of this
ticket — VBOOK-04 only gets a working schema, engine, and plain CRUD repositories in
place. VBOOK-06's design builds directly on top of what's specified here.

## Docker Compose & environment

**`docker-compose.yml`** (new, repo root): one `db` service, `postgres:16`, with:
- `POSTGRES_USER=booksy`, `POSTGRES_PASSWORD=booksy`, `POSTGRES_DB=booksy`
- port `5432:5432`
- a named volume for data persistence across container restarts
- `./docker/init-test-db.sql` mounted into `/docker-entrypoint-initdb.d/`, containing
  `CREATE DATABASE booksy_test;` — Postgres only runs `initdb.d` scripts on first
  container creation (empty data dir), so this runs once and both databases persist
  in the same volume thereafter.

**Environment variables** (`.env.example` gains, alongside the existing ElevenLabs
vars):
```text
DATABASE_URL=postgresql+asyncpg://booksy:booksy@localhost:5432/booksy
TEST_DATABASE_URL=postgresql+asyncpg://booksy:booksy@localhost:5432/booksy_test
```
`app/db.py` reads `DATABASE_URL` from the environment with the above as its default
(so `uv run uvicorn app.main:app` works out of the box against the compose setup with
zero configuration). Tests read `TEST_DATABASE_URL` the same way.

## Engine, session, and the FastAPI dependency

**`app/db.py`** (new):

```python
import os

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://booksy:booksy@localhost:5432/booksy"
)

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

`echo=True` is deliberate — this is a learning project, and seeing the generated SQL for
every request is the fastest way to build intuition for what the ORM is doing.

The `async with AsyncSessionLocal() as session:` line is the ticket's first learning
objective made concrete: the session is opened for the lifetime of the request and
closed automatically (returning its connection to the pool) when the generator exits,
success or failure, without an explicit `try`/`finally`.

Mutating repository methods additionally use `async with session.begin():` internally
(see below) — the ticket's second learning objective — to demarcate the transaction
boundary explicitly, rather than relying on session-level autocommit behavior.

## Data model

**`app/models.py`** (new), SQLAlchemy 2.0 typed declarative style:

```python
from sqlalchemy import ForeignKey, Table, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


employee_services = Table(
    "employee_services",
    Base.metadata,
    Column("employee_id", ForeignKey("employees.id"), primary_key=True),
    Column("service_id", ForeignKey("services.id"), primary_key=True),
)


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]

    employees: Mapped[list["Employee"]] = relationship(back_populates="business")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    duration_minutes: Mapped[int]
    price: Mapped[float]

    employees: Mapped[list["Employee"]] = relationship(
        secondary=employee_services, back_populates="services"
    )


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"))

    business: Mapped[Business] = relationship(back_populates="employees")
    services: Mapped[list[Service]] = relationship(
        secondary=employee_services, back_populates="employees"
    )


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(primary_key=True)
    customer_name: Mapped[str]
    service: Mapped[str]
    slot: Mapped[str]
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    status: Mapped[str]
```

Notes:
- IDs stay `String` primary keys, matching today's human-readable slugs
  (`biz-glow-salon`, `emp-alice`, `svc-haircut`) and `Booking.id`'s existing
  `str(uuid4())` — no switch to a native `UUID` column type.
- `employee_services` replaces `Employee.service_ids: list[str]` with a real
  many-to-many table + `relationship()` on both sides, so `search_employees` becomes a
  SQL join instead of Python list filtering.
- `Booking.employee_id` stays nullable **at the schema level** in this ticket — VBOOK-06
  is what makes it required at the API/validation level. VBOOK-04 is schema-and-plumbing
  only; changing `CreateBookingRequest` validation belongs to VBOOK-06's design.
- `slot`/`status` stay plain `String` columns (no `Enum`/`DateTime` type upgrade) — out
  of scope; matches today's dict shape exactly to keep this a persistence-only change.

## Repositories

Each `SqlAlchemy*Repository` takes an `AsyncSession` in `__init__` and exposes the same
method names as its in-memory predecessor, converting ORM rows to dicts before
returning. Example (`app/repositories/services.py`):

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Service


def _to_dict(service: Service) -> dict[str, str | int | float]:
    return {
        "id": service.id,
        "name": service.name,
        "duration_minutes": service.duration_minutes,
        "price": service.price,
    }


class SqlAlchemyServiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(self, name: str | None = None) -> list[dict[str, str | int | float]]:
        query = select(Service)
        if name is not None:
            query = query.where(Service.name.ilike(f"%{name}%"))
        result = await self._session.execute(query)
        return [_to_dict(service) for service in result.scalars()]

    async def get(self, service_id: str) -> dict[str, str | int | float]:
        service = await self._session.get(Service, service_id)
        if service is None:
            raise KeyError(service_id)
        return _to_dict(service)


def get_service_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyServiceRepository:
    return SqlAlchemyServiceRepository(session)
```

`InMemoryEmployeeRepository.search(service_id=...)` becomes a join through
`employee_services` (`select(Employee).join(Employee.services).where(Service.id ==
service_id)`), exercising the ticket's "joins"/"relationships" learning objectives
directly.

`SqlAlchemyBookingRepository.add(...)` wraps its insert in `async with
session.begin():` explicitly (rather than relying on session-level autocommit), per
the ticket's second learning objective:

```python
async def add(
    self, customer_name: str, service: str, slot: str, employee_id: str | None = None
) -> dict[str, str | None]:
    booking = Booking(
        id=str(uuid4()),
        customer_name=customer_name,
        service=service,
        slot=slot,
        employee_id=employee_id,
        status="confirmed",
    )
    async with self._session.begin():
        self._session.add(booking)
    return _to_dict(booking)
```

`cancel`/`reschedule`/`get` follow the same `session.get(Booking, booking_id)` +
`KeyError` pattern as `get_service_repository.get` above, preserving the existing
`except KeyError: raise HTTPException(404, ...)` handling in routers unchanged.

Routers change only by adding `async`/`await` (e.g. `async def search_services(...)`,
`services = await repository.search(name)`) — no signature or response-shape changes.

## Migrations

Alembic, initialized with the **async template** (`alembic init -t async alembic`), so
`alembic/env.py` runs migrations through an async engine/connection — consistent with
the rest of the app rather than dropping to a sync driver just for migrations. One
initial migration (`alembic revision --autogenerate`) creates `businesses`, `services`,
`employees`, `employee_services`, and `bookings` with their columns, primary keys,
foreign keys, and the `employee_services` composite primary key. `alembic upgrade head`
against the `booksy` database is a documented manual step (README), not run
automatically by the app.

## Seed script

**`scripts/seed_db.py`** (new, async): connects via `AsyncSessionLocal`, checks whether
`businesses` already has rows (`select(func.count()).select_from(Business)`), and if
not, inserts the same seed data currently hardcoded across the in-memory repositories —
2 businesses, 3 services, 6 employees (with their `employee_services` links matching
today's `service_ids` lists). Idempotent by that emptiness check, so re-running it after
data already exists is a no-op rather than a duplicate-key error. Run manually via `uv
run python -m scripts.seed_db`; never invoked from `app/main.py`.

## Testing

**Dependencies:** adds `sqlalchemy>=2.0`, `asyncpg`, `alembic`. Test-side async support
comes from the `anyio` pytest plugin, already pulled in transitively by
FastAPI/httpx/starlette — no new test dependency.

**Test client:** every test file switches from the synchronous
`TestClient(app)` to:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

(the `anyio_backend` fixture and `pytestmark` line move to a shared `tests/conftest.py`
so every test file just imports `client` and writes `async def test_...(client): ...`).
Existing call sites (`client.get(...)`, `client.post(...)`) are unaffected beyond adding
`await` and marking the test function `async def` — httpx's `AsyncClient` has the same
method names as `TestClient`.

**DB isolation** (`tests/conftest.py`, new):

```python
import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db import get_session
from app.main import app
from app.models import Base
from tests.seed_data import seed_reference_data  # shared with scripts/seed_db.py

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://booksy:booksy@localhost:5432/booksy_test"
)
test_engine = create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="session", autouse=True)
async def _schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(test_engine) as session:
        await seed_reference_data(session)
        await session.commit()


@pytest.fixture(autouse=True)
async def _isolated_session():
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn)

        async def override_get_session():
            yield session

        app.dependency_overrides[get_session] = override_get_session
        try:
            yield
        finally:
            await trans.rollback()
            app.dependency_overrides.pop(get_session, None)
```

Every test runs inside a transaction opened before it and rolled back after — the
standard SQLAlchemy test-isolation pattern. Schema and reference data (businesses,
services, employees) are created once per test session; each test starts from that
seeded state and any bookings/businesses it creates vanish on rollback. This replaces
the ad hoc `app.dependency_overrides[get_booking_repository] = ...` pattern
`tests/test_availability.py` introduced in VBOOK-09 for the same purpose (isolating one
test's booking from others) — that workaround is deleted since the new autouse fixture
handles isolation for every test uniformly.

`seed_reference_data` is factored into a small shared helper (e.g.
`tests/seed_data.py`) so both `scripts/seed_db.py` and the test fixture insert identical
businesses/services/employees from one source of truth, rather than duplicating the
seed dataset in two places.

**Existing test files** (`test_businesses.py`, `test_bookings.py`, `test_employees.py`,
`test_services.py`, `test_availability.py`, `test_slots.py`, `test_idempotency.py`) are
updated mechanically: `def test_...():` → `async def test_...(client):`, `client.get(...)`
→ `await client.get(...)`, and the module-level `client = TestClient(app)` line removed
in favor of the fixture. `test_slots.py` needs no changes — `generate_available_slots`
is a pure function with no DB dependency. `test_idempotency.py` needs no changes either
— `InMemoryIdempotencyStore` is untouched by this ticket.

## Out of scope

- Real conflict/overlap detection and locking for booking creation — VBOOK-06.
- Moving the in-memory idempotency store to Postgres.
- Changing `employee_id` from optional to required on `CreateBookingRequest` — VBOOK-06.
- `slot`/`status` type upgrades (e.g. real `DateTime`/`Enum` columns) — the schema
  mirrors today's string-typed dict fields exactly.
- Connection pool tuning, read replicas, or any other production-hardening concern.
