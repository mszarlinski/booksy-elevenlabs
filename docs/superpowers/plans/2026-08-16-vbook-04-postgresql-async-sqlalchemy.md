# VBOOK-04 — Add PostgreSQL and async SQLAlchemy — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every in-memory repository (businesses, employees, services, bookings) with real PostgreSQL persistence via async SQLAlchemy 2.x, behind a ports-and-adapters boundary so no database session or SQLAlchemy type ever appears in router code.

**Architecture:** `app/repositories/*.py` become pure `typing.Protocol` ports (zero SQLAlchemy import). `app/adapters/db/*.py` holds the engine/session, the SQLAlchemy ORM models, the `SqlAlchemy*Repository` adapters implementing each port, and the `get_*_repository` FastAPI dependency factories. Routers import the port (for typing) and the factory (for `Depends(...)`) — nothing else changes about them beyond `async`/`await`.

**Tech Stack:** FastAPI, Pydantic, pytest (existing); adds SQLAlchemy 2.x, `asyncpg`, Alembic (async template), the `anyio` pytest plugin (already a transitive dependency, no new install needed) for async test functions.

**Design reference:** [Spec](../specs/2026-08-16-vbook-04-postgresql-async-sqlalchemy-design.md)

**Run tests with:** `uv run pytest -q`

**Prerequisite from Task 1 onward:** a local Postgres must be running via `docker compose up -d db` — the test suite talks to a real database starting at Task 7, not mocks.

---

### Task 1: Postgres service in docker-compose, test database, env vars

**Files:**
- Modify: `docker-compose.yml`
- Create: `docker/init-test-db.sql`
- Modify: `.env.example`

- [ ] **Step 1: Add the `db` service and wire `api` to it**

Replace the full contents of `docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: booksy
      POSTGRES_PASSWORD: booksy
      POSTGRES_DB: booksy
    ports:
      - "5432:5432"
    volumes:
      - booksy-db-data:/var/lib/postgresql/data
      - ./docker/init-test-db.sql:/docker-entrypoint-initdb.d/init-test-db.sql

  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql+asyncpg://booksy:booksy@db:5432/booksy

volumes:
  booksy-db-data:
```

- [ ] **Step 2: Create the test-database init script**

```sql
-- docker/init-test-db.sql
CREATE DATABASE booksy_test;
```

- [ ] **Step 3: Add `DATABASE_URL`/`TEST_DATABASE_URL` to `.env.example`**

Add to the end of `.env.example`:

```text
DATABASE_URL=postgresql+asyncpg://booksy:booksy@localhost:5432/booksy
TEST_DATABASE_URL=postgresql+asyncpg://booksy:booksy@localhost:5432/booksy_test
```

- [ ] **Step 4: Start Postgres and verify both databases exist**

Run: `docker compose up -d db`
Then: `docker compose exec db psql -U booksy -d booksy -c "\l"`
Expected: the output lists both `booksy` and `booksy_test` databases.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml docker/init-test-db.sql .env.example
git commit -m "Add Postgres service and test database to docker-compose"
```

---

### Task 2: Add SQLAlchemy, asyncpg, and Alembic dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add the dependencies**

Change:

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "elevenlabs>=2.0",
    "python-dotenv>=1.0",
]
```

to:

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "elevenlabs>=2.0",
    "python-dotenv>=1.0",
    "sqlalchemy>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
]
```

- [ ] **Step 2: Sync dependencies**

Run: `uv sync`
Expected: `sqlalchemy`, `asyncpg`, `alembic` (and transitive deps, including `anyio` if not already present) install into `.venv`; `uv.lock` updates.

- [ ] **Step 3: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all existing tests still pass (dependency changes don't touch app code yet).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "Add sqlalchemy, asyncpg, and alembic dependencies"
```

---

### Task 3: Database engine, session, and FastAPI dependency

**Files:**
- Create: `app/adapters/__init__.py`
- Create: `app/adapters/db/__init__.py`
- Create: `app/adapters/db/session.py`

- [ ] **Step 1: Create the package `__init__.py` files**

```python
# app/adapters/__init__.py
```

```python
# app/adapters/db/__init__.py
```

- [ ] **Step 2: Create the session module**

```python
# app/adapters/db/session.py
import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://booksy:booksy@localhost:5432/booksy"
)

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 3: Verify it imports and connects**

Run:

```bash
uv run python -c "
import asyncio
from app.adapters.db.session import engine

async def check():
    async with engine.connect() as conn:
        print('connected')

asyncio.run(check())
"
```

Expected: prints `connected` (requires `docker compose up -d db` from Task 1 to be running).

- [ ] **Step 4: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all existing tests still pass — nothing imports this module yet.

- [ ] **Step 5: Commit**

```bash
git add app/adapters/__init__.py app/adapters/db/__init__.py app/adapters/db/session.py
git commit -m "Add async SQLAlchemy engine, session, and FastAPI dependency"
```

---

### Task 4: SQLAlchemy models

**Files:**
- Create: `app/adapters/db/models.py`

- [ ] **Step 1: Write the models**

```python
# app/adapters/db/models.py
from sqlalchemy import Column, ForeignKey, Table
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

- [ ] **Step 2: Verify the models import cleanly and metadata is populated**

Run: `uv run python -c "from app.adapters.db.models import Base; print(sorted(Base.metadata.tables.keys()))"`
Expected: `['bookings', 'businesses', 'employee_services', 'employees', 'services']`

- [ ] **Step 3: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all existing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add app/adapters/db/models.py
git commit -m "Add SQLAlchemy models for businesses, services, employees, bookings"
```

---

### Task 5: Alembic setup and initial migration

**Files:**
- Create: `alembic/` (via `alembic init -t async`)
- Modify: `alembic/env.py`
- Modify: `alembic.ini`
- Create: `alembic/versions/<generated>_initial_schema.py` (autogenerated)

- [ ] **Step 1: Initialize Alembic with the async template**

Run: `uv run alembic init -t async alembic`
Expected: creates `alembic.ini` and `alembic/` (`env.py`, `script.py.mako`, `versions/`).

- [ ] **Step 2: Point Alembic at the app's models and `DATABASE_URL`**

In `alembic/env.py`, replace:

```python
target_metadata = None
```

with:

```python
from app.adapters.db.models import Base

target_metadata = Base.metadata
```

Then, in `alembic/env.py`, find the line that reads the URL from config (in the async
template, inside `run_migrations_online`, something like
`connectable = async_engine_from_config(config.get_section(config.config_ini_section, {}), ...)`)
and immediately before that line, add:

```python
import os

config.set_main_option(
    "sqlalchemy.url",
    os.environ.get("DATABASE_URL", "postgresql+asyncpg://booksy:booksy@localhost:5432/booksy"),
)
```

This keeps Alembic's connection string in sync with `app/adapters/db/session.py`'s
default instead of duplicating it as a static value in `alembic.ini`.

- [ ] **Step 3: Generate the initial migration**

Run: `uv run alembic revision --autogenerate -m "initial schema"`
Expected: creates a file under `alembic/versions/` with `upgrade()`/`downgrade()`
functions creating `businesses`, `services`, `employees`, `employee_services`, and
`bookings`.

- [ ] **Step 4: Apply the migration to the dev database**

Run: `uv run alembic upgrade head`
Expected: exits cleanly; prints the applied revision.

- [ ] **Step 5: Verify the tables exist**

Run: `docker compose exec db psql -U booksy -d booksy -c "\dt"`
Expected: lists `businesses`, `services`, `employees`, `employee_services`, `bookings`,
`alembic_version`.

- [ ] **Step 6: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add alembic.ini alembic
git commit -m "Add Alembic with initial schema migration"
```

---

### Task 6: Shared seed data and seed script

**Files:**
- Create: `scripts/seed_data.py`
- Create: `scripts/seed_db.py`

- [ ] **Step 1: Write the shared seed data module**

```python
# scripts/seed_data.py
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import Business, Employee, Service

BUSINESSES = [
    {"id": "biz-glow-salon", "name": "Glow Hair & Beauty Salon"},
    {"id": "biz-downtown-barber", "name": "Downtown Barbershop"},
]

SERVICES = [
    {"id": "svc-haircut", "name": "Men's Haircut", "duration_minutes": 30, "price": 40.0},
    {"id": "svc-shave", "name": "Shave", "duration_minutes": 20, "price": 25.0},
    {"id": "svc-manicure", "name": "Manicure", "duration_minutes": 45, "price": 35.0},
]

EMPLOYEES = [
    {
        "id": "emp-alice",
        "name": "Alice",
        "business_id": "biz-glow-salon",
        "service_ids": ["svc-haircut", "svc-shave"],
    },
    {
        "id": "emp-carol",
        "name": "Carol",
        "business_id": "biz-glow-salon",
        "service_ids": ["svc-manicure"],
    },
    {
        "id": "emp-dave",
        "name": "Dave",
        "business_id": "biz-glow-salon",
        "service_ids": ["svc-manicure"],
    },
    {
        "id": "emp-bob",
        "name": "Bob",
        "business_id": "biz-downtown-barber",
        "service_ids": ["svc-haircut", "svc-manicure"],
    },
    {
        "id": "emp-erin",
        "name": "Erin",
        "business_id": "biz-downtown-barber",
        "service_ids": ["svc-shave"],
    },
    {
        "id": "emp-frank",
        "name": "Frank",
        "business_id": "biz-downtown-barber",
        "service_ids": ["svc-shave"],
    },
]


async def seed_reference_data(session: AsyncSession) -> None:
    services_by_id = {}
    for data in SERVICES:
        service = Service(**data)
        session.add(service)
        services_by_id[service.id] = service

    for data in BUSINESSES:
        session.add(Business(**data))

    for data in EMPLOYEES:
        employee = Employee(id=data["id"], name=data["name"], business_id=data["business_id"])
        employee.services = [services_by_id[service_id] for service_id in data["service_ids"]]
        session.add(employee)

    await session.flush()
```

- [ ] **Step 2: Write the seed script**

```python
# scripts/seed_db.py
import asyncio

from sqlalchemy import func, select

from app.adapters.db.models import Business
from app.adapters.db.session import AsyncSessionLocal
from scripts.seed_data import seed_reference_data


async def main() -> None:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Business))
        if count:
            print("Database already seeded, skipping.")
            return
        await seed_reference_data(session)
        await session.commit()
        print("Seeded reference data.")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Run the seed script against the dev database**

Run: `uv run python -m scripts.seed_db`
Expected: prints `Seeded reference data.`

- [ ] **Step 4: Verify it's idempotent**

Run: `uv run python -m scripts.seed_db` again.
Expected: prints `Database already seeded, skipping.`

- [ ] **Step 5: Verify the data landed correctly**

Run: `docker compose exec db psql -U booksy -d booksy -c "SELECT count(*) FROM businesses;" -c "SELECT count(*) FROM employee_services;"`
Expected: `2` businesses, `8` employee_services rows (2+1+1+2+1+1 across the six employees).

- [ ] **Step 6: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
git add scripts/seed_data.py scripts/seed_db.py
git commit -m "Add seed script for businesses, services, and employees"
```

---

### Task 7: Async test infrastructure (client fixture, DB isolation)

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the shared test fixtures**

```python
# tests/conftest.py
import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.adapters.db.models import Base
from app.adapters.db.session import get_session
from app.main import app
from scripts.seed_data import seed_reference_data

pytestmark = pytest.mark.anyio

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://booksy:booksy@localhost:5432/booksy_test"
)
test_engine = create_async_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def _schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(test_engine) as session:
        await seed_reference_data(session)
        await session.commit()
    yield
    await test_engine.dispose()


@pytest.fixture
async def db_session():
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture(autouse=True)
def _override_get_session(db_session):
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    yield
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

- [ ] **Step 2: Verify the schema/seed fixture runs standalone**

Run: `uv run pytest tests/ -q --collect-only`
Expected: collection succeeds (fixtures aren't executed by `--collect-only`, but this
confirms no import errors). Requires `docker compose up -d db` running.

- [ ] **Step 3: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all existing tests still pass — no test file uses the new `client`/`db_session`
fixtures yet, and `_schema`/`_override_get_session` being autouse doesn't affect the
still-synchronous `InMemory*Repository`-backed routers.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "Add async test client and Postgres transaction-isolation fixtures"
```

---

### Task 8: Business port + adapter + router

**Files:**
- Modify: `app/repositories/businesses.py` (becomes the port)
- Create: `app/adapters/db/businesses.py` (the adapter)
- Modify: `app/routers/businesses.py`
- Modify: `tests/test_businesses.py`

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `tests/test_businesses.py`:

```python
# tests/test_businesses.py
async def test_businesses_returns_seeded_businesses(client):
    response = await client.get("/businesses")

    assert response.status_code == 200
    names = {business["name"] for business in response.json()["businesses"]}
    assert {"Glow Hair & Beauty Salon", "Downtown Barbershop"} <= names


async def test_create_business_adds_a_new_business(client):
    await client.post("/businesses", json={"name": "Barber"})

    response = await client.get("/businesses")

    assert response.status_code == 200
    names = {business["name"] for business in response.json()["businesses"]}
    assert "Barber" in names
```

- [ ] **Step 2: Run tests to confirm the current (in-memory) behavior**

Run: `uv run pytest tests/test_businesses.py -v`
Expected: PASS. This is a persistence swap, not a behavior change — FastAPI runs sync
route handlers under `AsyncClient` exactly like it does under `TestClient` (both go
through the same ASGI app), so these tests already pass against
`InMemoryBusinessRepository`. Their job here is to lock in current behavior so Steps
3–5 can't silently change it; the real proof that Postgres is now involved comes from
Task 13's `curl`/restart check.

- [ ] **Step 3: Write the port**

Replace the full contents of `app/repositories/businesses.py`:

```python
# app/repositories/businesses.py
from typing import Protocol


class BusinessRepository(Protocol):
    async def list(self) -> list[dict[str, str]]: ...

    async def add(self, business: dict[str, str]) -> None: ...
```

- [ ] **Step 4: Write the adapter**

```python
# app/adapters/db/businesses.py
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import Business
from app.adapters.db.session import get_session


def _to_dict(business: Business) -> dict[str, str]:
    return {"id": business.id, "name": business.name}


class SqlAlchemyBusinessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[dict[str, str]]:
        result = await self._session.execute(select(Business))
        return [_to_dict(business) for business in result.scalars()]

    async def add(self, business: dict[str, str]) -> None:
        async with self._session.begin():
            self._session.add(Business(id=business["id"], name=business["name"]))


def get_business_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyBusinessRepository:
    return SqlAlchemyBusinessRepository(session)
```

- [ ] **Step 5: Update the router**

Replace the full contents of `app/routers/businesses.py`:

```python
# app/routers/businesses.py
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.adapters.db.businesses import get_business_repository
from app.repositories.businesses import BusinessRepository

router = APIRouter()


class BusinessHttpBody(BaseModel):
    name: str


@router.get("/businesses")
async def get_businesses(
    repository: BusinessRepository = Depends(get_business_repository),
) -> dict[str, list[dict[str, str]]]:
    return {"businesses": await repository.list()}


@router.post("/businesses")
async def create_business(
    business: BusinessHttpBody,
    repository: BusinessRepository = Depends(get_business_repository),
) -> dict[str, str]:
    created = {"id": str(uuid4()), "name": business.name}
    await repository.add(created)
    return created
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_businesses.py -v`
Expected: PASS (2 tests)

- [ ] **Step 7: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all other test files still pass (they don't touch businesses).

- [ ] **Step 7a: Confirm data really landed in Postgres, not just in memory**

Run: `docker compose exec db psql -U booksy -d booksy -c "SELECT name FROM businesses;"`
Expected: lists the two seeded businesses plus any created by `test_create_business_adds_a_new_business`
if it ran most recently (its own transaction rolls back, so don't worry if "Barber"
isn't present — the seeded two always are). This is the check that actually
distinguishes "still in-memory" from "now Postgres", since Step 6's assertions alone
would pass identically either way.

- [ ] **Step 8: Commit**

```bash
git add app/repositories/businesses.py app/adapters/db/businesses.py app/routers/businesses.py tests/test_businesses.py
git commit -m "Move business repository behind a port/adapter backed by Postgres"
```

---

### Task 9: Service port + adapter + router

**Files:**
- Modify: `app/repositories/services.py` (becomes the port)
- Create: `app/adapters/db/services.py` (the adapter)
- Modify: `app/routers/services.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `tests/test_services.py`:

```python
# tests/test_services.py
async def test_search_services_returns_seeded_services_when_no_filter(client):
    response = await client.get("/services")

    assert response.status_code == 200
    names = {service["name"] for service in response.json()["services"]}
    assert "Men's Haircut" in names


async def test_search_services_filters_by_name_case_insensitive_substring(client):
    response = await client.get("/services", params={"name": "haircut"})

    assert response.status_code == 200
    services = response.json()["services"]
    assert len(services) == 1
    assert services[0]["name"] == "Men's Haircut"


async def test_search_services_returns_empty_list_when_no_match(client):
    response = await client.get("/services", params={"name": "nonexistent-service"})

    assert response.status_code == 200
    assert response.json() == {"services": []}
```

- [ ] **Step 2: Run tests to confirm the current (in-memory) behavior**

Run: `uv run pytest tests/test_services.py -v`
Expected: PASS — same reasoning as Task 8: this is a persistence swap with no outward
behavior change, so these tests already pass against `InMemoryServiceRepository`. They
exist to lock in current behavior across the upcoming implementation swap.

- [ ] **Step 3: Write the port**

Replace the full contents of `app/repositories/services.py`:

```python
# app/repositories/services.py
from typing import Protocol


class ServiceRepository(Protocol):
    async def search(self, name: str | None = None) -> list[dict[str, str | int | float]]: ...

    async def get(self, service_id: str) -> dict[str, str | int | float]: ...
```

- [ ] **Step 4: Write the adapter**

```python
# app/adapters/db/services.py
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import Service
from app.adapters.db.session import get_session


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

- [ ] **Step 5: Update the router**

Replace the full contents of `app/routers/services.py`:

```python
# app/routers/services.py
import logging

from fastapi import APIRouter, Depends

from app.adapters.db.services import get_service_repository
from app.repositories.services import ServiceRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/services")
async def search_services(
    name: str | None = None,
    repository: ServiceRepository = Depends(get_service_repository),
) -> dict[str, list[dict[str, str | int | float]]]:
    logger.info("tool_request tool=search_services name=%s", name)
    services = await repository.search(name)
    logger.info("tool_response tool=search_services result_count=%d", len(services))
    return {"services": services}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_services.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Run the full suite and note the one expected failure**

Run: `uv run pytest -q`
Expected: `tests/test_availability.py` now fails with a collection error —
`app/routers/availability.py` still does
`from app.repositories.services import InMemoryServiceRepository, get_service_repository`,
and `app/repositories/services.py` no longer has either name (Step 3 replaced them with
the `ServiceRepository` protocol). This is expected and tracked: `app/routers/availability.py`
depends on services, employees, *and* bookings, so it can only be fixed once all three
are ported — that happens in Task 11 (Step 9 onward), which also fixes this failure.
Every other test file passes.

- [ ] **Step 8: Commit**

```bash
git add app/repositories/services.py app/adapters/db/services.py app/routers/services.py tests/test_services.py
git commit -m "Move service repository behind a port/adapter backed by Postgres"
```

---

### Task 10: Employee port + adapter (many-to-many join) + router

**Files:**
- Modify: `app/repositories/employees.py` (becomes the port)
- Create: `app/adapters/db/employees.py` (the adapter)
- Modify: `app/routers/employees.py`
- Modify: `tests/test_employees.py`

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `tests/test_employees.py`:

```python
# tests/test_employees.py
async def test_search_employees_returns_seeded_employees_when_no_filter(client):
    response = await client.get("/employees")

    assert response.status_code == 200
    names = {employee["name"] for employee in response.json()["employees"]}
    assert names == {"Alice", "Bob", "Carol", "Dave", "Erin", "Frank"}


async def test_search_employees_filters_by_service_id(client):
    response = await client.get("/employees", params={"service_id": "svc-shave"})

    assert response.status_code == 200
    employees = response.json()["employees"]
    assert {employee["name"] for employee in employees} == {"Alice", "Erin", "Frank"}


async def test_search_employees_returns_empty_list_for_unknown_service(client):
    response = await client.get("/employees", params={"service_id": "svc-unknown"})

    assert response.status_code == 200
    assert response.json() == {"employees": []}
```

- [ ] **Step 2: Run tests to confirm the current (in-memory) behavior**

Run: `uv run pytest tests/test_employees.py -v`
Expected: PASS — same reasoning as Task 8/9: this is a persistence swap with no outward
behavior change, so these tests already pass against `InMemoryEmployeeRepository`. They
exist to lock in current behavior across the upcoming implementation swap.

- [ ] **Step 3: Write the port**

Replace the full contents of `app/repositories/employees.py`:

```python
# app/repositories/employees.py
from typing import Protocol


class EmployeeRepository(Protocol):
    async def search(self, service_id: str | None = None) -> list[dict[str, str | list[str]]]: ...

    async def list(self) -> list[dict[str, str | list[str]]]: ...

    async def get(self, employee_id: str) -> dict[str, str | list[str]]: ...
```

- [ ] **Step 4: Write the adapter**

```python
# app/adapters/db/employees.py
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.db.models import Employee, Service
from app.adapters.db.session import get_session


def _to_dict(employee: Employee) -> dict[str, str | list[str]]:
    return {
        "id": employee.id,
        "name": employee.name,
        "business_id": employee.business_id,
        "service_ids": [service.id for service in employee.services],
    }


class SqlAlchemyEmployeeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(self, service_id: str | None = None) -> list[dict[str, str | list[str]]]:
        query = select(Employee).options(selectinload(Employee.services))
        if service_id is not None:
            query = query.join(Employee.services).where(Service.id == service_id)
        result = await self._session.execute(query)
        return [_to_dict(employee) for employee in result.scalars()]

    async def list(self) -> list[dict[str, str | list[str]]]:
        return await self.search(None)

    async def get(self, employee_id: str) -> dict[str, str | list[str]]:
        query = (
            select(Employee)
            .options(selectinload(Employee.services))
            .where(Employee.id == employee_id)
        )
        result = await self._session.execute(query)
        employee = result.scalar_one_or_none()
        if employee is None:
            raise KeyError(employee_id)
        return _to_dict(employee)


def get_employee_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyEmployeeRepository:
    return SqlAlchemyEmployeeRepository(session)
```

`selectinload(Employee.services)` eagerly loads each employee's services in one extra
query (rather than N+1 lazy loads per employee) — the join in `search(service_id=...)`
is a separate, filtering join against `employee_services`/`services`; the `selectinload`
is what populates `.services` for the dict conversion afterward.

- [ ] **Step 5: Update the router**

Replace the full contents of `app/routers/employees.py`:

```python
# app/routers/employees.py
import logging

from fastapi import APIRouter, Depends

from app.adapters.db.employees import get_employee_repository
from app.repositories.employees import EmployeeRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/employees")
async def search_employees(
    service_id: str | None = None,
    repository: EmployeeRepository = Depends(get_employee_repository),
) -> dict[str, list[dict[str, str | list[str]]]]:
    logger.info("tool_request tool=search_employees service_id=%s", service_id)
    employees = await repository.search(service_id)
    logger.info("tool_response tool=search_employees result_count=%d", len(employees))
    return {"employees": employees}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_employees.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Run the full suite and note the one expected failure**

Run: `uv run pytest -q`
Expected: `tests/test_availability.py` still fails with the same collection error as
after Task 9 — `app/routers/availability.py` also imports
`InMemoryEmployeeRepository`/`get_employee_repository` from `app.repositories.employees`,
which Step 3 just removed too. Still expected, still fixed in Task 11 (Step 9 onward).
Every other test file passes.

- [ ] **Step 8: Commit**

```bash
git add app/repositories/employees.py app/adapters/db/employees.py app/routers/employees.py tests/test_employees.py
git commit -m "Move employee repository behind a port/adapter with a real many-to-many join"
```

---

### Task 11: Booking port + adapter + router, and the availability router

**Files:**
- Modify: `app/repositories/bookings.py` (becomes the port)
- Create: `app/adapters/db/bookings.py` (the adapter)
- Modify: `app/routers/bookings.py`
- Modify: `tests/test_bookings.py`
- Modify: `app/idempotency.py` (made async — Step 5a)
- Modify: `tests/test_idempotency.py` (Step 5b)
- Modify: `app/routers/availability.py` (Step 11 — depends on all three ported repositories)
- Modify: `tests/test_availability.py` (Step 9)

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `tests/test_bookings.py`:

```python
# tests/test_bookings.py
from app.adapters.db.bookings import SqlAlchemyBookingRepository, get_booking_repository
from app.main import app


class CountingBookingRepository(SqlAlchemyBookingRepository):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.cancel_calls = 0
        self.reschedule_calls = 0

    async def cancel(self, booking_id: str) -> dict[str, str | None]:
        self.cancel_calls += 1
        return await super().cancel(booking_id)

    async def reschedule(self, booking_id: str, slot: str) -> dict[str, str | None]:
        self.reschedule_calls += 1
        return await super().reschedule(booking_id, slot)


async def test_bookings_returns_200_and_empty_list(client):
    response = await client.get("/bookings")

    assert response.status_code == 200
    assert response.json() == {"bookings": []}


async def test_create_booking_returns_confirmed_booking(client):
    response = await client.post(
        "/bookings",
        json={
            "customer_name": "Alice",
            "service": "Haircut",
            "slot": "2026-09-15T18:00",
            "confirmed": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["customer_name"] == "Alice"
    assert body["service"] == "Haircut"
    assert body["slot"] == "2026-09-15T18:00"
    assert body["status"] == "confirmed"
    assert "id" in body


async def test_create_booking_rejects_missing_confirmed_field(client):
    response = await client.post(
        "/bookings",
        json={"customer_name": "Oscar", "service": "Haircut", "slot": "2026-09-15T20:00"},
    )

    assert response.status_code == 422


async def test_create_booking_rejects_confirmed_false(client):
    response = await client.post(
        "/bookings",
        json={
            "customer_name": "Peggy",
            "service": "Haircut",
            "slot": "2026-09-15T21:00",
            "confirmed": False,
        },
    )

    assert response.status_code == 400


async def test_cancel_booking_sets_status_to_cancelled(client):
    created = (
        await client.post(
            "/bookings",
            json={
                "customer_name": "Bob",
                "service": "Shave",
                "slot": "2026-09-15T19:00",
                "confirmed": True,
            },
        )
    ).json()

    response = await client.post(f"/bookings/{created['id']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


async def test_reschedule_booking_updates_slot(client):
    created = (
        await client.post(
            "/bookings",
            json={
                "customer_name": "Carol",
                "service": "Haircut",
                "slot": "2026-09-15T10:00",
                "confirmed": True,
            },
        )
    ).json()

    response = await client.post(
        f"/bookings/{created['id']}/reschedule", json={"slot": "2026-09-16T10:00"}
    )

    assert response.status_code == 200
    assert response.json()["slot"] == "2026-09-16T10:00"


async def test_create_booking_is_idempotent_on_retry(client):
    request = {
        "customer_name": "Dana",
        "service": "Haircut",
        "slot": "2026-09-17T10:00",
        "confirmed": True,
    }
    headers = {"Idempotency-Key": "retry-key-1"}

    first = await client.post("/bookings", json=request, headers=headers)
    second = await client.post("/bookings", json=request, headers=headers)

    assert first.json() == second.json()

    bookings = (await client.get("/bookings")).json()["bookings"]
    matching = [b for b in bookings if b["id"] == first.json()["id"]]
    assert len(matching) == 1


async def test_cancel_booking_does_not_repeat_mutation_on_retry(client, db_session):
    counting_repo = CountingBookingRepository(db_session)
    app.dependency_overrides[get_booking_repository] = lambda: counting_repo
    try:
        created = (
            await client.post(
                "/bookings",
                json={
                    "customer_name": "Eve",
                    "service": "Haircut",
                    "slot": "2026-09-18T10:00",
                    "confirmed": True,
                },
            )
        ).json()
        headers = {"Idempotency-Key": "cancel-retry-key-1"}

        await client.post(f"/bookings/{created['id']}/cancel", headers=headers)
        await client.post(f"/bookings/{created['id']}/cancel", headers=headers)

        assert counting_repo.cancel_calls == 1
    finally:
        app.dependency_overrides.pop(get_booking_repository, None)


async def test_create_booking_accepts_optional_employee_id(client):
    response = await client.post(
        "/bookings",
        json={
            "customer_name": "Grace",
            "service": "Haircut",
            "slot": "2026-09-21T10:00",
            "confirmed": True,
            "employee_id": "emp-alice",
        },
    )

    assert response.status_code == 200
    assert response.json()["employee_id"] == "emp-alice"


async def test_create_booking_without_employee_id_defaults_to_none(client):
    response = await client.post(
        "/bookings",
        json={
            "customer_name": "Heidi",
            "service": "Haircut",
            "slot": "2026-09-21T11:00",
            "confirmed": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["employee_id"] is None


async def test_get_booking_returns_the_booking(client):
    created = (
        await client.post(
            "/bookings",
            json={
                "customer_name": "Ivan",
                "service": "Haircut",
                "slot": "2026-09-22T09:00",
                "confirmed": True,
            },
        )
    ).json()

    response = await client.get(f"/bookings/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


async def test_get_booking_returns_404_for_unknown_id(client):
    response = await client.get("/bookings/does-not-exist")

    assert response.status_code == 404


async def test_reschedule_booking_does_not_repeat_mutation_on_retry(client, db_session):
    counting_repo = CountingBookingRepository(db_session)
    app.dependency_overrides[get_booking_repository] = lambda: counting_repo
    try:
        created = (
            await client.post(
                "/bookings",
                json={
                    "customer_name": "Frank",
                    "service": "Haircut",
                    "slot": "2026-09-19T10:00",
                    "confirmed": True,
                },
            )
        ).json()
        headers = {"Idempotency-Key": "reschedule-retry-key-1"}
        body = {"slot": "2026-09-20T10:00"}

        await client.post(f"/bookings/{created['id']}/reschedule", json=body, headers=headers)
        await client.post(f"/bookings/{created['id']}/reschedule", json=body, headers=headers)

        assert counting_repo.reschedule_calls == 1
    finally:
        app.dependency_overrides.pop(get_booking_repository, None)


async def test_get_customer_bookings_filters_case_insensitive_substring(client):
    await client.post(
        "/bookings",
        json={
            "customer_name": "Judy Smith",
            "service": "Haircut",
            "slot": "2026-09-23T09:00",
            "confirmed": True,
        },
    )
    await client.post(
        "/bookings",
        json={
            "customer_name": "Mallory",
            "service": "Shave",
            "slot": "2026-09-23T10:00",
            "confirmed": True,
        },
    )

    response = await client.get("/bookings", params={"customer_name": "judy"})

    assert response.status_code == 200
    bookings = response.json()["bookings"]
    assert len(bookings) == 1
    assert bookings[0]["customer_name"] == "Judy Smith"


async def test_get_customer_bookings_returns_empty_list_when_no_match(client):
    response = await client.get("/bookings", params={"customer_name": "nobody-with-this-name"})

    assert response.status_code == 200
    assert response.json() == {"bookings": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bookings.py -v`
Expected: ERROR at collection — `app.adapters.db.bookings` doesn't exist yet, and the
test file imports `SqlAlchemyBookingRepository`/`get_booking_repository` from it.
Proceed to the implementation steps.

- [ ] **Step 3: Write the port**

Replace the full contents of `app/repositories/bookings.py`:

```python
# app/repositories/bookings.py
from typing import Protocol


class BookingRepository(Protocol):
    async def list(self) -> list[dict[str, str | None]]: ...

    async def add(
        self,
        customer_name: str,
        service: str,
        slot: str,
        employee_id: str | None = None,
    ) -> dict[str, str | None]: ...

    async def cancel(self, booking_id: str) -> dict[str, str | None]: ...

    async def reschedule(self, booking_id: str, slot: str) -> dict[str, str | None]: ...

    async def get(self, booking_id: str) -> dict[str, str | None]: ...
```

Same shape as the other three ports — just the protocol, no factory function. The
factory (`get_booking_repository`) lives in the adapter module (Step 4); both the router
and `tests/test_bookings.py`'s `app.dependency_overrides[...]` import it from there.

- [ ] **Step 4: Write the adapter**

```python
# app/adapters/db/bookings.py
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.db.models import Booking
from app.adapters.db.session import get_session


def _to_dict(booking: Booking) -> dict[str, str | None]:
    return {
        "id": booking.id,
        "customer_name": booking.customer_name,
        "service": booking.service,
        "slot": booking.slot,
        "employee_id": booking.employee_id,
        "status": booking.status,
    }


class SqlAlchemyBookingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[dict[str, str | None]]:
        result = await self._session.execute(select(Booking))
        return [_to_dict(booking) for booking in result.scalars()]

    async def add(
        self,
        customer_name: str,
        service: str,
        slot: str,
        employee_id: str | None = None,
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

    async def cancel(self, booking_id: str) -> dict[str, str | None]:
        async with self._session.begin():
            booking = await self._session.get(Booking, booking_id)
            if booking is None:
                raise KeyError(booking_id)
            booking.status = "cancelled"
        return _to_dict(booking)

    async def reschedule(self, booking_id: str, slot: str) -> dict[str, str | None]:
        async with self._session.begin():
            booking = await self._session.get(Booking, booking_id)
            if booking is None:
                raise KeyError(booking_id)
            booking.slot = slot
        return _to_dict(booking)

    async def get(self, booking_id: str) -> dict[str, str | None]:
        booking = await self._session.get(Booking, booking_id)
        if booking is None:
            raise KeyError(booking_id)
        return _to_dict(booking)


def get_booking_repository(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyBookingRepository:
    return SqlAlchemyBookingRepository(session)
```

- [ ] **Step 5: Update the router**

Replace the full contents of `app/routers/bookings.py`:

```python
# app/routers/bookings.py
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.adapters.db.bookings import get_booking_repository
from app.idempotency import InMemoryIdempotencyStore, get_idempotency_store, maybe_idempotent
from app.repositories.bookings import BookingRepository

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateBookingRequest(BaseModel):
    customer_name: str
    service: str
    slot: str
    confirmed: bool
    employee_id: str | None = None


class RescheduleBookingRequest(BaseModel):
    slot: str


@router.get("/bookings")
async def get_bookings(
    customer_name: str | None = None,
    repository: BookingRepository = Depends(get_booking_repository),
) -> dict[str, list[dict[str, str | None]]]:
    bookings = await repository.list()
    if customer_name is not None:
        logger.info("tool_request tool=get_customer_bookings customer_name_filter=true")
        needle = customer_name.lower()
        bookings = [b for b in bookings if needle in b["customer_name"].lower()]
        logger.info("tool_response tool=get_customer_bookings result_count=%d", len(bookings))
    return {"bookings": bookings}


@router.get("/bookings/{booking_id}")
async def get_booking(
    booking_id: str,
    repository: BookingRepository = Depends(get_booking_repository),
) -> dict[str, str | None]:
    logger.info("tool_request tool=get_booking booking_id=%s", booking_id)
    try:
        booking = await repository.get(booking_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown booking_id: {booking_id}")
    logger.info(
        "tool_response tool=get_booking booking_id=%s status=%s", booking_id, booking["status"]
    )
    return booking


@router.post("/bookings")
async def create_booking(
    body: CreateBookingRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    repository: BookingRepository = Depends(get_booking_repository),
    idempotency: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> dict[str, str | None]:
    logger.info(
        "tool_request tool=create_booking service=%s slot=%s employee_id=%s confirmed=%s",
        body.service,
        body.slot,
        body.employee_id,
        body.confirmed,
    )
    if not body.confirmed:
        raise HTTPException(
            status_code=400,
            detail="booking must be explicitly confirmed by the customer before creation",
        )
    booking = await maybe_idempotent(
        idempotency_key,
        idempotency,
        lambda: repository.add(body.customer_name, body.service, body.slot, body.employee_id),
    )
    logger.info("tool_response tool=create_booking booking_id=%s", booking["id"])
    return booking


@router.post("/bookings/{booking_id}/cancel")
async def cancel_booking(
    booking_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    repository: BookingRepository = Depends(get_booking_repository),
    idempotency: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> dict[str, str | None]:
    return await maybe_idempotent(
        idempotency_key, idempotency, lambda: repository.cancel(booking_id)
    )


@router.post("/bookings/{booking_id}/reschedule")
async def reschedule_booking(
    booking_id: str,
    body: RescheduleBookingRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    repository: BookingRepository = Depends(get_booking_repository),
    idempotency: InMemoryIdempotencyStore = Depends(get_idempotency_store),
) -> dict[str, str | None]:
    return await maybe_idempotent(
        idempotency_key, idempotency, lambda: repository.reschedule(booking_id, body.slot)
    )
```

Note this calls `await maybe_idempotent(...)` — `maybe_idempotent` itself must become
`async def` and `await` the `mutate` callable, since `repository.add`/`.cancel`/
`.reschedule` are now coroutines. That change belongs to `app/idempotency.py`, made in
Step 5a below (kept as its own step since it's a different file than the router).

- [ ] **Step 5a: Make `maybe_idempotent`/`get_or_create` async**

In `app/idempotency.py`, change:

```python
    def get_or_create(self, key: str, compute: Callable[[], dict]) -> dict:
        with self._lock:
            cached = self._get(key)
            if cached is not None:
                return cached

            result = compute()
            self._entries[key] = (result, self._clock() + self._ttl)
            return result
```

to:

```python
    async def get_or_create(self, key: str, compute: Callable[[], Awaitable[dict]]) -> dict:
        async with self._async_lock:
            cached = self._get(key)
            if cached is not None:
                return cached

            result = await compute()
            self._entries[key] = (result, self._clock() + self._ttl)
            return result
```

Change the imports and `__init__` to add an `asyncio.Lock` (the existing
`threading.Lock` no longer applies — nothing in this class touches multiple OS threads
now, everything runs on the single event loop, and `asyncio.Lock` is what correctly
serializes concurrent coroutines against each other):

```python
import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone

DEFAULT_TTL = timedelta(hours=24)


class InMemoryIdempotencyStore:
    def __init__(
        self,
        ttl: timedelta = DEFAULT_TTL,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._ttl = ttl
        self._clock = clock
        self._entries: dict[str, tuple[dict, datetime]] = {}
        self._async_lock = asyncio.Lock()
```

And change `maybe_idempotent` to:

```python
async def maybe_idempotent(
    idempotency_key: str | None,
    idempotency: InMemoryIdempotencyStore,
    mutate: Callable[[], Awaitable[dict]],
) -> dict:
    if idempotency_key is None:
        return await mutate()
    return await idempotency.get_or_create(idempotency_key, mutate)
```

`tests/test_idempotency.py`'s `test_get_or_create_computes_exactly_once_under_concurrent_access`
test (using `ThreadPoolExecutor`) is dropped rather than converted — no multi-threading
or concurrency simulation in the unit test suite; see Step 5b.

- [ ] **Step 5b: Update `tests/test_idempotency.py` for the async API**

Replace the full contents of `tests/test_idempotency.py`:

```python
# tests/test_idempotency.py
from datetime import datetime, timedelta, timezone

from app.idempotency import InMemoryIdempotencyStore


async def test_get_or_create_computes_result_for_unknown_key():
    store = InMemoryIdempotencyStore()

    async def compute():
        return {"id": "1"}

    result = await store.get_or_create("abc", compute)

    assert result == {"id": "1"}


async def test_get_or_create_returns_cached_result_without_recomputing():
    store = InMemoryIdempotencyStore()
    calls = []

    async def compute_one():
        calls.append(1)
        return {"id": "1"}

    async def compute_two():
        calls.append(2)
        return {"id": "2"}

    await store.get_or_create("abc", compute_one)
    result = await store.get_or_create("abc", compute_two)

    assert result == {"id": "1"}
    assert calls == [1]


async def test_get_or_create_recomputes_after_ttl_expires():
    current = datetime(2026, 1, 1, tzinfo=timezone.utc)
    store = InMemoryIdempotencyStore(ttl=timedelta(seconds=10), clock=lambda: current)

    async def compute_one():
        return {"id": "1"}

    async def compute_two():
        return {"id": "2"}

    await store.get_or_create("abc", compute_one)
    current = current + timedelta(seconds=11)
    result = await store.get_or_create("abc", compute_two)

    assert result == {"id": "2"}
```

This file has no HTTP/DB dependency, so it doesn't need the `client` fixture — it does,
however, run under `pytestmark = pytest.mark.anyio` from `tests/conftest.py`, which is
why every test function here is `async def`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_bookings.py tests/test_idempotency.py -v`
Expected: PASS (all tests in both files)

- [ ] **Step 7: Run the full suite and confirm which failure remains**

Run: `uv run pytest -q`
Expected: `tests/test_availability.py` still fails with the same collection error noted
after Tasks 9 and 10 — `app/routers/availability.py` still imports from
`app.repositories.bookings` names that no longer exist. Every other file passes. Steps
9–14 below fix this now that services, employees, and bookings are all ported (the
availability router is the one place that depends on all three, so it has to wait for
all three — this is the last task, not a separate one).

- [ ] **Step 8: Commit the booking port/adapter/router**

```bash
git add app/repositories/bookings.py app/adapters/db/bookings.py app/routers/bookings.py app/idempotency.py tests/test_bookings.py tests/test_idempotency.py
git commit -m "Move booking repository behind a port/adapter and make idempotency async"
```

- [ ] **Step 9: Write the failing availability tests**

Replace the full contents of `tests/test_availability.py`:

```python
# tests/test_availability.py
async def test_search_available_slots_returns_slots_for_a_service(client):
    response = await client.get(
        "/availability", params={"service_id": "svc-haircut", "date": "2026-09-24"}
    )

    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) > 0
    assert all(slot["employee_id"] in {"emp-alice", "emp-bob"} for slot in slots)


async def test_search_available_slots_filters_by_employee_id(client):
    response = await client.get(
        "/availability",
        params={"service_id": "svc-haircut", "date": "2026-09-24", "employee_id": "emp-bob"},
    )

    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) > 0
    assert all(slot["employee_id"] == "emp-bob" for slot in slots)


async def test_search_available_slots_excludes_an_existing_booking(client):
    created = (
        await client.post(
            "/bookings",
            json={
                "customer_name": "Trent",
                "service": "Men's Haircut",
                "slot": "2026-09-24T10:00",
                "confirmed": True,
                "employee_id": "emp-alice",
            },
        )
    ).json()
    assert created["status"] == "confirmed"

    response = await client.get(
        "/availability",
        params={
            "service_id": "svc-haircut",
            "date": "2026-09-24",
            "employee_id": "emp-alice",
        },
    )

    starts = {slot["start"] for slot in response.json()["slots"]}
    assert "2026-09-24T10:00" not in starts


async def test_search_available_slots_returns_404_for_unknown_service(client):
    response = await client.get(
        "/availability", params={"service_id": "svc-unknown", "date": "2026-09-24"}
    )

    assert response.status_code == 404


async def test_search_available_slots_returns_400_for_malformed_date(client):
    response = await client.get(
        "/availability", params={"service_id": "svc-haircut", "date": "not-a-date"}
    )

    assert response.status_code == 400
```

This drops the `InMemoryBookingRepository`/`app.dependency_overrides` workaround the
original VBOOK-09 version of this test used — the `db_session`-per-test transaction
rollback fixture from `tests/conftest.py` already isolates this booking from every other
test, so the workaround is unnecessary.

- [ ] **Step 10: Run tests to verify they fail**

Run: `uv run pytest tests/test_availability.py -v`
Expected: ERROR at collection, same as after Tasks 9/10 — `app/routers/availability.py`
still imports `InMemoryServiceRepository`/`InMemoryEmployeeRepository`/
`InMemoryBookingRepository` names that no longer exist anywhere in
`app/repositories/`. Proceed to Step 11.

- [ ] **Step 11: Update the router**

Replace the full contents of `app/routers/availability.py`:

```python
# app/routers/availability.py
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.adapters.db.bookings import get_booking_repository
from app.adapters.db.employees import get_employee_repository
from app.adapters.db.services import get_service_repository
from app.repositories.bookings import BookingRepository
from app.repositories.employees import EmployeeRepository
from app.repositories.services import ServiceRepository
from app.slots import generate_available_slots

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/availability")
async def search_available_slots(
    service_id: str,
    date: str,
    earliest_time: str | None = None,
    latest_time: str | None = None,
    employee_id: str | None = None,
    service_repository: ServiceRepository = Depends(get_service_repository),
    employee_repository: EmployeeRepository = Depends(get_employee_repository),
    booking_repository: BookingRepository = Depends(get_booking_repository),
) -> dict[str, list[dict[str, str]]]:
    logger.info(
        "tool_request tool=search_available_slots service_id=%s date=%s "
        "earliest_time=%s latest_time=%s employee_id=%s",
        service_id,
        date,
        earliest_time,
        latest_time,
        employee_id,
    )
    try:
        service = await service_repository.get(service_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown service_id: {service_id}")

    try:
        slots = generate_available_slots(
            service=service,
            employees=await employee_repository.list(),
            bookings=await booking_repository.list(),
            date=date,
            earliest_time=earliest_time,
            latest_time=latest_time,
            employee_id=employee_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info("tool_response tool=search_available_slots result_count=%d", len(slots))
    return {"slots": slots}
```

- [ ] **Step 12: Run tests to verify they pass**

Run: `uv run pytest tests/test_availability.py -v`
Expected: PASS (5 tests)

- [ ] **Step 13: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all tests pass — every router now runs against Postgres, with no known
failures remaining.

- [ ] **Step 14: Commit**

```bash
git add app/routers/availability.py tests/test_availability.py
git commit -m "Make availability router async and drop the in-memory test workaround"
```

---

### Task 12: Update main.py imports and confirm the full suite

**Files:**
- Modify: `app/main.py` (if needed)

- [ ] **Step 1: Check whether `app/main.py` needs changes**

`app/main.py` only imports router modules and calls `app.include_router(...)` — none of
that changed shape (router objects are still `APIRouter()` instances). Read the current
file:

```python
import logging

from fastapi import FastAPI

from app.routers import availability, bookings, businesses, employees, services

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.include_router(businesses.router)
app.include_router(bookings.router)
app.include_router(services.router)
app.include_router(employees.router)
app.include_router(availability.router)
```

No changes needed — leave as-is.

- [ ] **Step 2: Run the full suite**

Run: `uv run pytest -q`
Expected: all tests pass, including `tests/test_slots.py` (pure function, untouched)
and `tests/test_idempotency.py` (updated in Task 11).

- [ ] **Step 3: Manually verify the running app against Postgres**

Run: `uv run uvicorn app.main:app --reload` (in one terminal), then in another:
`curl -s localhost:8000/businesses | python3 -m json.tool`
Expected: JSON listing the two seeded businesses (proves the app is reading from
Postgres, not stale in-memory state). Stop the app with Ctrl-C afterward.

- [ ] **Step 4: Verify restart preserves data (the ticket's acceptance criteria)**

With the app stopped, run: `docker compose restart db`, wait a few seconds, then repeat
Step 3's `curl` command.
Expected: same businesses list — proves data survived a database restart, not just an
app restart.

- [ ] **Step 5: Commit (only if Step 1 required an edit; otherwise skip)**

```bash
git add app/main.py
git commit -m "Confirm main.py wiring is unchanged after the Postgres migration"
```

---

### Task 13: Documentation and backlog updates

**Files:**
- Modify: `README.md`
- Modify: `docs/BACKLOG.md`
- Move: `docs/backlog/VBOOK-04-add-postgresql-and-async-sqlalchemy.md` → `docs/done/VBOOK-04-add-postgresql-and-async-sqlalchemy.md`

- [ ] **Step 1: Update the "How it works" diagram in README.md**

Change:

```text
      ├─ app/routers/*.py       — HTTP endpoints (services, employees, availability, bookings, businesses)
      ├─ app/repositories/*.py  — in-memory data stores (no database yet — see VBOOK-04)
      └─ app/slots.py           — pure availability/slot-generation logic
```

to:

```text
      ├─ app/routers/*.py        — HTTP endpoints (services, employees, availability, bookings, businesses)
      ├─ app/repositories/*.py   — ports: typing.Protocol interfaces, no database import
      ├─ app/adapters/db/*.py    — adapters: SQLAlchemy models, session, and repository implementations
      └─ app/slots.py            — pure availability/slot-generation logic
```

- [ ] **Step 2: Update the "Tech stack" section**

After the `pytest` + `TestClient` bullet, add:

```markdown
- **[PostgreSQL](https://www.postgresql.org/)** + **[SQLAlchemy](https://www.sqlalchemy.org/) 2.x** (async, via `asyncpg`) + **[Alembic](https://alembic.sqlalchemy.org/)** — real persistence for businesses, services, employees, and bookings, behind a ports-and-adapters boundary (`app/repositories/` = ports, `app/adapters/db/` = adapters)
```

Also update the `pytest` bullet, since `TestClient` is no longer what's used:

```markdown
- **pytest** + httpx's `AsyncClient` (ASGI transport) — the automated test suite, isolated per-test via a rolled-back Postgres transaction
```

- [ ] **Step 3: Update "Project structure"**

Change:

```text
  repositories/           — in-memory data stores (seeded sample data, no persistence yet)
```

to:

```text
  repositories/           — ports: typing.Protocol interfaces (no database import)
  adapters/db/            — adapters: SQLAlchemy models, session, and Postgres-backed repositories
```

- [ ] **Step 4: Add a "Database" subsection to "Getting started"**

After the "Run locally" subsection, add:

```markdown
### Database

```bash
docker compose up -d db
uv run alembic upgrade head
uv run python -m scripts.seed_db
```
```

- [ ] **Step 4a: Update the "Project status" section**

Change:

```markdown
This is a learning project, built incrementally per [`docs/BACKLOG.md`](docs/BACKLOG.md).
As of now: FastAPI skeleton, in-memory booking domain, idempotent mutations, and
read-only ElevenLabs tool integration are done. Real persistence (PostgreSQL) and
voice-driven booking creation are upcoming stories — see the backlog for the full plan.
```

to:

```markdown
This is a learning project, built incrementally per [`docs/BACKLOG.md`](docs/BACKLOG.md).
As of now: FastAPI skeleton, real PostgreSQL persistence, idempotent mutations, and
ElevenLabs tool integration (including voice-driven booking creation) are done.
Concurrency-safe booking creation (VBOOK-06) is the next story — see the backlog for the
full plan.
```

- [ ] **Step 5: Move the backlog file to done**

```bash
git mv docs/backlog/VBOOK-04-add-postgresql-and-async-sqlalchemy.md docs/done/VBOOK-04-add-postgresql-and-async-sqlalchemy.md
```

- [ ] **Step 6: Update the link in `docs/BACKLOG.md`**

Change:

```text
| [VBOOK-04](backlog/VBOOK-04-add-postgresql-and-async-sqlalchemy.md) | P0 | Add PostgreSQL and async SQLAlchemy |
```

to:

```text
| [VBOOK-04](done/VBOOK-04-add-postgresql-and-async-sqlalchemy.md) | P0 | Add PostgreSQL and async SQLAlchemy |
```

- [ ] **Step 7: Run the full suite one last time**

Run: `uv run pytest -q`
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add README.md docs/BACKLOG.md docs/backlog docs/done
git commit -m "Mark VBOOK-04 as done"
```
