# VBOOK-09 — Connect ElevenLabs tools to FastAPI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose five read-only tools (`search_services`, `search_employees`, `search_available_slots`, `get_booking`, `get_customer_bookings`) over plain REST endpoints, backed by minimal in-memory stand-ins for services/employees/availability, and write (but do not execute) a script that registers these as ElevenLabs webhook tools on an agent.

**Architecture:** New `services` and `employees` in-memory repositories follow the existing `InMemory*Repository` + `get_*_repository` pattern (`app/repositories/businesses.py`). A pure `app/slots.py` module computes available slots from fixed working hours, service duration, and existing bookings. Five REST endpoints across four routers (`services`, `employees`, `availability`, and an extended `bookings`) expose this. A standalone `scripts/create_elevenlabs_agent.py` builds ElevenLabs webhook tool configs pointing at these endpoints.

**Tech Stack:** FastAPI, Pydantic, pytest + `TestClient` (existing); adds `elevenlabs` and `python-dotenv`.

**Design references:** [Spec](../specs/2026-08-16-vbook-09-elevenlabs-tools-design.md), [ADR 0001](../../adr/0001-elevenlabs-tool-layer-architecture.md)

**Run tests with:** `uv run pytest <path> -v` (confirmed working — 13 tests currently pass with `uv run pytest -q`)

---

### Task 1: Service repository + `GET /services`

**Files:**
- Create: `app/repositories/services.py`
- Create: `app/routers/services.py`
- Modify: `app/main.py`
- Test: `tests/test_services.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_services.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_services_returns_seeded_services_when_no_filter():
    response = client.get("/services")

    assert response.status_code == 200
    names = {service["name"] for service in response.json()["services"]}
    assert "Men's Haircut" in names


def test_search_services_filters_by_name_case_insensitive_substring():
    response = client.get("/services", params={"name": "haircut"})

    assert response.status_code == 200
    services = response.json()["services"]
    assert len(services) == 1
    assert services[0]["name"] == "Men's Haircut"


def test_search_services_returns_empty_list_when_no_match():
    response = client.get("/services", params={"name": "nonexistent-service"})

    assert response.status_code == 200
    assert response.json() == {"services": []}
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_services.py -v`
Expected: FAIL — `ModuleNotFoundError` or 404, since `app/repositories/services.py`, `app/routers/services.py` don't exist yet and `/services` isn't routed.

- [x] **Step 3: Create the service repository**

```python
# app/repositories/services.py
class InMemoryServiceRepository:
    def __init__(self) -> None:
        self._services: list[dict[str, str | int | float]] = [
            {
                "id": "svc-haircut",
                "name": "Men's Haircut",
                "duration_minutes": 30,
                "price": 40.0,
            },
            {
                "id": "svc-shave",
                "name": "Shave",
                "duration_minutes": 20,
                "price": 25.0,
            },
            {
                "id": "svc-manicure",
                "name": "Manicure",
                "duration_minutes": 45,
                "price": 35.0,
            },
        ]

    def search(self, name: str | None = None) -> list[dict[str, str | int | float]]:
        if name is None:
            return self._services
        needle = name.lower()
        return [service for service in self._services if needle in service["name"].lower()]

    def get(self, service_id: str) -> dict[str, str | int | float]:
        for service in self._services:
            if service["id"] == service_id:
                return service
        raise KeyError(service_id)


_repository = InMemoryServiceRepository()


def get_service_repository() -> InMemoryServiceRepository:
    return _repository
```

- [x] **Step 4: Create the services router**

```python
# app/routers/services.py
import logging

from fastapi import APIRouter, Depends

from app.repositories.services import InMemoryServiceRepository, get_service_repository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/services")
def search_services(
    name: str | None = None,
    repository: InMemoryServiceRepository = Depends(get_service_repository),
) -> dict[str, list[dict[str, str | int | float]]]:
    logger.info("tool_request tool=search_services name=%s", name)
    services = repository.search(name)
    logger.info("tool_response tool=search_services result_count=%d", len(services))
    return {"services": services}
```

- [x] **Step 5: Wire the router into the app and enable INFO logging**

```python
# app/main.py
import logging

from fastapi import FastAPI

from app.routers import bookings, businesses, services

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.include_router(businesses.router)
app.include_router(bookings.router)
app.include_router(services.router)
```

- [x] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_services.py -v`
Expected: PASS (3 tests)

- [x] **Step 7: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all tests pass (13 existing + 3 new = 16)

- [x] **Step 8: Commit**

```bash
git add app/repositories/services.py app/routers/services.py app/main.py tests/test_services.py
git commit -m "Add search_services tool via GET /services"
```

---

### Task 2: Employee repository + `GET /employees`

**Files:**
- Create: `app/repositories/employees.py`
- Create: `app/routers/employees.py`
- Modify: `app/main.py`
- Test: `tests/test_employees.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_employees.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_employees_returns_seeded_employees_when_no_filter():
    response = client.get("/employees")

    assert response.status_code == 200
    names = {employee["name"] for employee in response.json()["employees"]}
    assert names == {"Alice", "Bob"}


def test_search_employees_filters_by_service_id():
    response = client.get("/employees", params={"service_id": "svc-shave"})

    assert response.status_code == 200
    employees = response.json()["employees"]
    assert [employee["name"] for employee in employees] == ["Alice"]


def test_search_employees_returns_empty_list_for_unknown_service():
    response = client.get("/employees", params={"service_id": "svc-unknown"})

    assert response.status_code == 200
    assert response.json() == {"employees": []}
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_employees.py -v`
Expected: FAIL — module/route doesn't exist yet.

- [x] **Step 3: Create the employee repository**

```python
# app/repositories/employees.py
class InMemoryEmployeeRepository:
    def __init__(self) -> None:
        self._employees: list[dict[str, str | list[str]]] = [
            {
                "id": "emp-alice",
                "name": "Alice",
                "service_ids": ["svc-haircut", "svc-shave"],
            },
            {
                "id": "emp-bob",
                "name": "Bob",
                "service_ids": ["svc-haircut", "svc-manicure"],
            },
        ]

    def search(self, service_id: str | None = None) -> list[dict[str, str | list[str]]]:
        if service_id is None:
            return self._employees
        return [
            employee for employee in self._employees if service_id in employee["service_ids"]
        ]

    def list(self) -> list[dict[str, str | list[str]]]:
        return self._employees

    def get(self, employee_id: str) -> dict[str, str | list[str]]:
        for employee in self._employees:
            if employee["id"] == employee_id:
                return employee
        raise KeyError(employee_id)


_repository = InMemoryEmployeeRepository()


def get_employee_repository() -> InMemoryEmployeeRepository:
    return _repository
```

- [x] **Step 4: Create the employees router**

```python
# app/routers/employees.py
import logging

from fastapi import APIRouter, Depends

from app.repositories.employees import InMemoryEmployeeRepository, get_employee_repository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/employees")
def search_employees(
    service_id: str | None = None,
    repository: InMemoryEmployeeRepository = Depends(get_employee_repository),
) -> dict[str, list[dict[str, str | list[str]]]]:
    logger.info("tool_request tool=search_employees service_id=%s", service_id)
    employees = repository.search(service_id)
    logger.info("tool_response tool=search_employees result_count=%d", len(employees))
    return {"employees": employees}
```

- [x] **Step 5: Wire the router into the app**

```python
# app/main.py
import logging

from fastapi import FastAPI

from app.routers import bookings, businesses, employees, services

logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.include_router(businesses.router)
app.include_router(bookings.router)
app.include_router(services.router)
app.include_router(employees.router)
```

- [x] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_employees.py -v`
Expected: PASS (3 tests)

- [x] **Step 7: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all tests pass (16 existing + 3 new = 19)

- [x] **Step 8: Commit**

```bash
git add app/repositories/employees.py app/routers/employees.py app/main.py tests/test_employees.py
git commit -m "Add search_employees tool via GET /employees"
```

---

### Task 3: Add `employee_id` to the booking model

**Files:**
- Modify: `app/repositories/bookings.py`
- Modify: `app/routers/bookings.py:12-16` (`CreateBookingRequest`) and `:39-50` (`create_booking`)
- Test: `tests/test_bookings.py`

- [x] **Step 1: Write the failing test**

Add to `tests/test_bookings.py`:

```python
def test_create_booking_accepts_optional_employee_id():
    response = client.post(
        "/bookings",
        json={
            "customer_name": "Grace",
            "service": "Haircut",
            "slot": "2026-08-21T10:00",
            "employee_id": "emp-alice",
        },
    )

    assert response.status_code == 200
    assert response.json()["employee_id"] == "emp-alice"


def test_create_booking_without_employee_id_defaults_to_none():
    response = client.post(
        "/bookings",
        json={"customer_name": "Heidi", "service": "Haircut", "slot": "2026-08-21T11:00"},
    )

    assert response.status_code == 200
    assert response.json()["employee_id"] is None
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bookings.py -v`
Expected: FAIL on the two new tests — `CreateBookingRequest` rejects/ignores `employee_id`, and the stored booking has no `employee_id` key (`KeyError` or assertion failure).

- [x] **Step 3: Update the booking repository**

```python
# app/repositories/bookings.py
from uuid import uuid4


class InMemoryBookingRepository:
    def __init__(self) -> None:
        self._bookings: list[dict[str, str | None]] = []

    def list(self) -> list[dict[str, str | None]]:
        return self._bookings

    def add(
        self,
        customer_name: str,
        service: str,
        slot: str,
        employee_id: str | None = None,
    ) -> dict[str, str | None]:
        booking = {
            "id": str(uuid4()),
            "customer_name": customer_name,
            "service": service,
            "slot": slot,
            "employee_id": employee_id,
            "status": "confirmed",
        }
        self._bookings.append(booking)
        return booking

    def cancel(self, booking_id: str) -> dict[str, str | None]:
        booking = self.get(booking_id)
        booking["status"] = "cancelled"
        return booking

    def reschedule(self, booking_id: str, slot: str) -> dict[str, str | None]:
        booking = self.get(booking_id)
        booking["slot"] = slot
        return booking

    def get(self, booking_id: str) -> dict[str, str | None]:
        for booking in self._bookings:
            if booking["id"] == booking_id:
                return booking
        raise KeyError(booking_id)


_repository = InMemoryBookingRepository()


def get_booking_repository() -> InMemoryBookingRepository:
    return _repository
```

Note: `_get` is renamed to `get` (a public lookup is needed by Task 4's `GET /bookings/{booking_id}` endpoint). `cancel`/`reschedule` are updated to call `self.get(...)`.

- [x] **Step 4: Update `CreateBookingRequest` and `create_booking`**

In `app/routers/bookings.py`, change:

```python
class CreateBookingRequest(BaseModel):
    customer_name: str
    service: str
    slot: str
```

to:

```python
class CreateBookingRequest(BaseModel):
    customer_name: str
    service: str
    slot: str
    employee_id: str | None = None
```

And change the `create_booking` handler's lambda:

```python
        lambda: repository.add(body.customer_name, body.service, body.slot),
```

to:

```python
        lambda: repository.add(body.customer_name, body.service, body.slot, body.employee_id),
```

- [x] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_bookings.py -v`
Expected: PASS (all tests in the file, including the two new ones)

- [x] **Step 6: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all tests pass (19 existing + 2 new = 21)

- [x] **Step 7: Commit**

```bash
git add app/repositories/bookings.py app/routers/bookings.py tests/test_bookings.py
git commit -m "Add optional employee_id to bookings"
```

---

### Task 4: `GET /bookings/{booking_id}` (get_booking tool)

**Files:**
- Modify: `app/routers/bookings.py`
- Test: `tests/test_bookings.py`

- [x] **Step 1: Write the failing tests**

Add to `tests/test_bookings.py`:

```python
def test_get_booking_returns_the_booking():
    created = client.post(
        "/bookings",
        json={"customer_name": "Ivan", "service": "Haircut", "slot": "2026-08-22T09:00"},
    ).json()

    response = client.get(f"/bookings/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_booking_returns_404_for_unknown_id():
    response = client.get("/bookings/does-not-exist")

    assert response.status_code == 404
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bookings.py -v`
Expected: FAIL — no route matches `GET /bookings/{booking_id}` yet (404 for both, but the first test expects 200).

- [x] **Step 3: Add the `get_booking` endpoint**

In `app/routers/bookings.py`, add `logging` and `HTTPException` imports and a `logger`:

```python
import logging
from collections.abc import Callable

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.idempotency import InMemoryIdempotencyStore, get_idempotency_store
from app.repositories.bookings import InMemoryBookingRepository, get_booking_repository

logger = logging.getLogger(__name__)

router = APIRouter()
```

Add the new handler directly after `get_bookings`:

```python
@router.get("/bookings/{booking_id}")
def get_booking(
    booking_id: str,
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
) -> dict[str, str | None]:
    logger.info("tool_request tool=get_booking booking_id=%s", booking_id)
    try:
        booking = repository.get(booking_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown booking_id: {booking_id}")
    logger.info(
        "tool_response tool=get_booking booking_id=%s status=%s", booking_id, booking["status"]
    )
    return booking
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_bookings.py -v`
Expected: PASS (all tests in the file)

- [x] **Step 5: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all tests pass (21 existing + 2 new = 23)

- [x] **Step 6: Commit**

```bash
git add app/routers/bookings.py tests/test_bookings.py
git commit -m "Add get_booking tool via GET /bookings/{booking_id}"
```

---

### Task 5: `GET /bookings?customer_name=` (get_customer_bookings tool)

**Files:**
- Modify: `app/routers/bookings.py`
- Test: `tests/test_bookings.py`

- [x] **Step 1: Write the failing tests**

Add to `tests/test_bookings.py`:

```python
def test_get_customer_bookings_filters_case_insensitive_substring():
    client.post(
        "/bookings",
        json={"customer_name": "Judy Smith", "service": "Haircut", "slot": "2026-08-23T09:00"},
    )
    client.post(
        "/bookings",
        json={"customer_name": "Mallory", "service": "Shave", "slot": "2026-08-23T10:00"},
    )

    response = client.get("/bookings", params={"customer_name": "judy"})

    assert response.status_code == 200
    bookings = response.json()["bookings"]
    assert len(bookings) == 1
    assert bookings[0]["customer_name"] == "Judy Smith"


def test_get_customer_bookings_returns_empty_list_when_no_match():
    response = client.get("/bookings", params={"customer_name": "nobody-with-this-name"})

    assert response.status_code == 200
    assert response.json() == {"bookings": []}
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_bookings.py -v`
Expected: FAIL — `GET /bookings` currently ignores `customer_name` and returns every booking, so the filtered assertions fail.

- [x] **Step 3: Update the `get_bookings` handler**

In `app/routers/bookings.py`, change:

```python
@router.get("/bookings")
def get_bookings(
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
) -> dict[str, list[dict[str, str]]]:
    return {"bookings": repository.list()}
```

to:

```python
@router.get("/bookings")
def get_bookings(
    customer_name: str | None = None,
    repository: InMemoryBookingRepository = Depends(get_booking_repository),
) -> dict[str, list[dict[str, str | None]]]:
    bookings = repository.list()
    if customer_name is not None:
        logger.info("tool_request tool=get_customer_bookings customer_name=%s", customer_name)
        needle = customer_name.lower()
        bookings = [b for b in bookings if needle in b["customer_name"].lower()]
        logger.info("tool_response tool=get_customer_bookings result_count=%d", len(bookings))
    return {"bookings": bookings}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_bookings.py -v`
Expected: PASS (all tests in the file)

- [x] **Step 5: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all tests pass (23 existing + 2 new = 25)

- [x] **Step 6: Commit**

```bash
git add app/routers/bookings.py tests/test_bookings.py
git commit -m "Add get_customer_bookings tool via GET /bookings?customer_name="
```

---

### Task 6: `app/slots.py` pure slot-generation function

**Files:**
- Create: `app/slots.py`
- Test: `tests/test_slots.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_slots.py
import pytest

from app.slots import generate_available_slots

SERVICE = {"id": "svc-haircut", "name": "Men's Haircut", "duration_minutes": 30, "price": 40.0}
EMPLOYEES = [
    {"id": "emp-alice", "name": "Alice", "service_ids": ["svc-haircut"]},
    {"id": "emp-bob", "name": "Bob", "service_ids": ["svc-haircut"]},
]


def test_generates_slots_within_working_hours():
    slots = generate_available_slots(SERVICE, EMPLOYEES, bookings=[], date="2026-08-20")

    starts = {slot["start"] for slot in slots if slot["employee_id"] == "emp-alice"}
    assert "2026-08-20T09:00" in starts
    assert "2026-08-20T16:30" in starts
    assert "2026-08-20T17:00" not in starts


def test_excludes_slot_that_would_run_past_closing_time():
    long_service = {**SERVICE, "duration_minutes": 45}

    slots = generate_available_slots(long_service, EMPLOYEES, bookings=[], date="2026-08-20")

    starts = {slot["start"] for slot in slots if slot["employee_id"] == "emp-alice"}
    assert "2026-08-20T16:00" in starts
    assert "2026-08-20T16:30" not in starts


def test_excludes_slots_with_existing_confirmed_booking_for_that_employee():
    bookings = [{"employee_id": "emp-alice", "slot": "2026-08-20T10:00", "status": "confirmed"}]

    slots = generate_available_slots(SERVICE, EMPLOYEES, bookings=bookings, date="2026-08-20")

    alice_starts = {slot["start"] for slot in slots if slot["employee_id"] == "emp-alice"}
    bob_starts = {slot["start"] for slot in slots if slot["employee_id"] == "emp-bob"}
    assert "2026-08-20T10:00" not in alice_starts
    assert "2026-08-20T10:00" in bob_starts


def test_ignores_cancelled_bookings():
    bookings = [{"employee_id": "emp-alice", "slot": "2026-08-20T10:00", "status": "cancelled"}]

    slots = generate_available_slots(SERVICE, EMPLOYEES, bookings=bookings, date="2026-08-20")

    alice_starts = {slot["start"] for slot in slots if slot["employee_id"] == "emp-alice"}
    assert "2026-08-20T10:00" in alice_starts


def test_filters_by_earliest_and_latest_time():
    slots = generate_available_slots(
        SERVICE,
        EMPLOYEES,
        bookings=[],
        date="2026-08-20",
        earliest_time="14:00",
        latest_time="15:00",
    )

    starts = sorted({slot["start"] for slot in slots if slot["employee_id"] == "emp-alice"})
    assert starts == ["2026-08-20T14:00", "2026-08-20T14:30", "2026-08-20T15:00"]


def test_filters_by_employee_id():
    slots = generate_available_slots(
        SERVICE, EMPLOYEES, bookings=[], date="2026-08-20", employee_id="emp-bob"
    )

    assert len(slots) > 0
    assert all(slot["employee_id"] == "emp-bob" for slot in slots)


def test_excludes_employees_who_do_not_perform_the_service():
    other_service = {"id": "svc-manicure", "name": "Manicure", "duration_minutes": 30, "price": 35.0}

    slots = generate_available_slots(other_service, EMPLOYEES, bookings=[], date="2026-08-20")

    assert slots == []


def test_raises_value_error_for_malformed_date():
    with pytest.raises(ValueError):
        generate_available_slots(SERVICE, EMPLOYEES, bookings=[], date="not-a-date")


def test_raises_value_error_for_malformed_time():
    with pytest.raises(ValueError):
        generate_available_slots(
            SERVICE, EMPLOYEES, bookings=[], date="2026-08-20", earliest_time="not-a-time"
        )
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_slots.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.slots'`

- [x] **Step 3: Implement `app/slots.py`**

```python
# app/slots.py
from datetime import date as date_cls, datetime, time, timedelta

WORKDAY_START = time(9, 0)
WORKDAY_END = time(17, 0)
SLOT_INTERVAL_MINUTES = 30


def generate_available_slots(
    service: dict[str, str | int | float],
    employees: list[dict[str, str | list[str]]],
    bookings: list[dict[str, str | None]],
    date: str,
    earliest_time: str | None = None,
    latest_time: str | None = None,
    employee_id: str | None = None,
) -> list[dict[str, str]]:
    try:
        search_date = date_cls.fromisoformat(date)
    except ValueError as exc:
        raise ValueError(f"invalid date: {date!r}, expected YYYY-MM-DD") from exc

    try:
        earliest = time.fromisoformat(earliest_time) if earliest_time else WORKDAY_START
        latest = time.fromisoformat(latest_time) if latest_time else WORKDAY_END
    except ValueError as exc:
        raise ValueError("invalid earliest_time/latest_time, expected HH:MM") from exc

    duration = timedelta(minutes=service["duration_minutes"])

    candidates = [employee for employee in employees if service["id"] in employee["service_ids"]]
    if employee_id is not None:
        candidates = [employee for employee in candidates if employee["id"] == employee_id]

    booked = {
        (booking.get("employee_id"), booking["slot"])
        for booking in bookings
        if booking["status"] == "confirmed"
    }

    day_start = datetime.combine(search_date, WORKDAY_START)
    day_end = datetime.combine(search_date, WORKDAY_END)

    slots = []
    for employee in candidates:
        current = day_start
        while current + duration <= day_end:
            start_time = current.time()
            if earliest <= start_time <= latest:
                key = (employee["id"], current.isoformat(timespec="minutes"))
                if key not in booked:
                    slots.append(
                        {
                            "employee_id": employee["id"],
                            "employee_name": employee["name"],
                            "start": current.isoformat(timespec="minutes"),
                            "end": (current + duration).isoformat(timespec="minutes"),
                        }
                    )
            current += timedelta(minutes=SLOT_INTERVAL_MINUTES)

    return slots
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_slots.py -v`
Expected: PASS (9 tests)

- [x] **Step 5: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all tests pass (25 existing + 9 new = 34)

- [x] **Step 6: Commit**

```bash
git add app/slots.py tests/test_slots.py
git commit -m "Add pure slot-generation logic for availability search"
```

---

### Task 7: `GET /availability` (search_available_slots tool)

**Files:**
- Create: `app/routers/availability.py`
- Modify: `app/main.py`
- Test: `tests/test_availability.py`

- [x] **Step 1: Write the failing tests**

```python
# tests/test_availability.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_search_available_slots_returns_slots_for_a_service():
    response = client.get(
        "/availability", params={"service_id": "svc-haircut", "date": "2026-08-24"}
    )

    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) > 0
    assert all(slot["employee_id"] in {"emp-alice", "emp-bob"} for slot in slots)


def test_search_available_slots_filters_by_employee_id():
    response = client.get(
        "/availability",
        params={"service_id": "svc-haircut", "date": "2026-08-24", "employee_id": "emp-bob"},
    )

    assert response.status_code == 200
    slots = response.json()["slots"]
    assert len(slots) > 0
    assert all(slot["employee_id"] == "emp-bob" for slot in slots)


def test_search_available_slots_excludes_an_existing_booking():
    created = client.post(
        "/bookings",
        json={
            "customer_name": "Trent",
            "service": "Men's Haircut",
            "slot": "2026-08-24T10:00",
            "employee_id": "emp-alice",
        },
    ).json()
    assert created["status"] == "confirmed"

    response = client.get(
        "/availability",
        params={"service_id": "svc-haircut", "date": "2026-08-24", "employee_id": "emp-alice"},
    )

    starts = {slot["start"] for slot in response.json()["slots"]}
    assert "2026-08-24T10:00" not in starts


def test_search_available_slots_returns_404_for_unknown_service():
    response = client.get(
        "/availability", params={"service_id": "svc-unknown", "date": "2026-08-24"}
    )

    assert response.status_code == 404


def test_search_available_slots_returns_400_for_malformed_date():
    response = client.get(
        "/availability", params={"service_id": "svc-haircut", "date": "not-a-date"}
    )

    assert response.status_code == 400
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_availability.py -v`
Expected: FAIL — no `/availability` route exists yet (404 for all, including the ones expecting 200/400).

**Deviation (found and fixed during Task 7's own implementation/review, before Task 7 was ever marked complete):** `test_search_available_slots_excludes_an_existing_booking` as written above posts a real booking through the shared module-level `InMemoryBookingRepository` singleton with no cleanup. Because pytest collects test files alphabetically (`test_availability.py` before `test_bookings.py`), this leaked a booking into shared state and broke `tests/test_bookings.py::test_bookings_returns_200_and_empty_list`. The committed version of this test instead uses an isolated repository via `app.dependency_overrides[get_booking_repository]`, restored in a `finally` block — mirroring the `CountingBookingRepository` override pattern already used in `tests/test_bookings.py`:

```python
def test_search_available_slots_excludes_an_existing_booking():
    isolated_repo = InMemoryBookingRepository()
    app.dependency_overrides[get_booking_repository] = lambda: isolated_repo
    try:
        created = client.post(
            "/bookings",
            json={
                "customer_name": "Trent",
                "service": "Men's Haircut",
                "slot": "2026-08-24T10:00",
                "employee_id": "emp-alice",
            },
        ).json()
        assert created["status"] == "confirmed"

        response = client.get(
            "/availability",
            params={
                "service_id": "svc-haircut",
                "date": "2026-08-24",
                "employee_id": "emp-alice",
            },
        )

        starts = {slot["start"] for slot in response.json()["slots"]}
        assert "2026-08-24T10:00" not in starts
    finally:
        app.dependency_overrides.pop(get_booking_repository, None)
```

This required adding `from app.repositories.bookings import InMemoryBookingRepository, get_booking_repository` and `from app.main import app` to `tests/test_availability.py`'s imports. Verified necessary by reverting to the unisolated version and reproducing the `test_bookings.py` failure, then restoring the fix. This was independently confirmed necessary and correctly scoped during Task 7's spec-compliance and code-quality review.

- [x] **Step 3: Create the availability router**

```python
# app/routers/availability.py
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.repositories.bookings import InMemoryBookingRepository, get_booking_repository
from app.repositories.employees import InMemoryEmployeeRepository, get_employee_repository
from app.repositories.services import InMemoryServiceRepository, get_service_repository
from app.slots import generate_available_slots

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/availability")
def search_available_slots(
    service_id: str,
    date: str,
    earliest_time: str | None = None,
    latest_time: str | None = None,
    employee_id: str | None = None,
    service_repository: InMemoryServiceRepository = Depends(get_service_repository),
    employee_repository: InMemoryEmployeeRepository = Depends(get_employee_repository),
    booking_repository: InMemoryBookingRepository = Depends(get_booking_repository),
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
        service = service_repository.get(service_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown service_id: {service_id}")

    try:
        slots = generate_available_slots(
            service=service,
            employees=employee_repository.list(),
            bookings=booking_repository.list(),
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

- [x] **Step 4: Wire the router into the app**

```python
# app/main.py
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

- [x] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_availability.py -v`
Expected: PASS (5 tests)

- [x] **Step 6: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all tests pass (34 existing + 5 new = 39)

- [x] **Step 7: Commit**

```bash
git add app/routers/availability.py app/main.py tests/test_availability.py
git commit -m "Add search_available_slots tool via GET /availability"
```

---

### Task 8: Dependencies and environment scaffolding for the agent script

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`
- Modify: `.gitignore`

- [x] **Step 1: Add dependencies to `pyproject.toml`**

Change:

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
]
```

to:

```toml
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "elevenlabs>=1.0",
    "python-dotenv>=1.0",
]
```

- [x] **Step 2: Sync dependencies**

Run: `uv sync`
Expected: `elevenlabs` and `python-dotenv` (and their transitive deps) get installed into `.venv`; `uv.lock` is updated.

- [x] **Step 3: Create `.env.example`**

```text
# .env.example
ELEVENLABS_API_KEY=
API_BASE_URL=http://localhost:8000
```

- [x] **Step 4: Add `.env` to `.gitignore`**

Change:

```text
__pycache__/
*.pyc
.venv/
.pytest_cache/
.DS_Store
```

to:

```text
__pycache__/
*.pyc
.venv/
.pytest_cache/
.DS_Store
.env
```

- [x] **Step 5: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all 39 tests still pass (dependency changes don't touch app code)

- [x] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock .env.example .gitignore
git commit -m "Add elevenlabs and python-dotenv dependencies"
```

---

### Task 9: ElevenLabs agent-creation script

**Files:**
- Create: `scripts/create_elevenlabs_agent.py`
- Test: `tests/test_create_elevenlabs_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_create_elevenlabs_agent.py
from scripts.create_elevenlabs_agent import build_tool_configs

BASE_URL = "http://localhost:8000"


def test_builds_one_config_per_tool():
    configs = build_tool_configs(BASE_URL)

    names = [config["name"] for config in configs]
    assert names == [
        "search_services",
        "search_employees",
        "search_available_slots",
        "get_booking",
        "get_customer_bookings",
    ]


def test_each_config_is_a_webhook_pointing_at_the_base_url():
    configs = build_tool_configs(BASE_URL)

    for config in configs:
        assert config["type"] == "webhook"
        assert config["api_schema"]["url"].startswith(BASE_URL)
        assert config["api_schema"]["method"] == "GET"


def test_search_available_slots_config_has_expected_query_params():
    configs = build_tool_configs(BASE_URL)
    slots_config = next(c for c in configs if c["name"] == "search_available_slots")

    assert slots_config["api_schema"]["url"] == f"{BASE_URL}/availability"
    query_params = slots_config["api_schema"]["query_params_schema"]
    assert set(query_params) == {
        "service_id",
        "date",
        "earliest_time",
        "latest_time",
        "employee_id",
    }


def test_get_booking_config_uses_a_path_param():
    configs = build_tool_configs(BASE_URL)
    get_booking_config = next(c for c in configs if c["name"] == "get_booking")

    assert get_booking_config["api_schema"]["url"] == f"{BASE_URL}/bookings/{{booking_id}}"
    assert "booking_id" in get_booking_config["api_schema"]["path_params_schema"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_create_elevenlabs_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts'` (the module doesn't exist yet)

- [ ] **Step 3: Create `scripts/__init__.py` so the script is importable as a module**

```python
# scripts/__init__.py
```

- [ ] **Step 4: Implement `scripts/create_elevenlabs_agent.py`**

```python
# scripts/create_elevenlabs_agent.py
import os

from dotenv import load_dotenv
from elevenlabs import ElevenLabs

DEFAULT_BASE_URL = "http://localhost:8000"

TOOL_DEFINITIONS = [
    {
        "name": "search_services",
        "description": (
            "Search for bookable services by name, e.g. 'haircut'. Use this to find "
            "the service_id needed by search_employees and search_available_slots."
        ),
        "path": "/services",
        "query_params": {
            "name": {
                "type": "string",
                "description": "Free-text search term matched against service names.",
            },
        },
    },
    {
        "name": "search_employees",
        "description": (
            "Search for employees who can perform a given service. Provide the "
            "service_id returned by search_services."
        ),
        "path": "/employees",
        "query_params": {
            "service_id": {
                "type": "string",
                "description": "The id of the service the employee must be able to perform.",
            },
        },
    },
    {
        "name": "search_available_slots",
        "description": (
            "Find available appointment slots for a service on a given date, "
            "optionally narrowed by time range or a specific employee."
        ),
        "path": "/availability",
        "query_params": {
            "service_id": {
                "type": "string",
                "description": "The id of the service to book, from search_services.",
            },
            "date": {
                "type": "string",
                "description": "The date to search, formatted YYYY-MM-DD.",
            },
            "earliest_time": {
                "type": "string",
                "description": "Optional earliest allowed start time, formatted HH:MM.",
            },
            "latest_time": {
                "type": "string",
                "description": "Optional latest allowed start time, formatted HH:MM.",
            },
            "employee_id": {
                "type": "string",
                "description": "Optional id of a specific employee, from search_employees.",
            },
        },
    },
    {
        "name": "get_booking",
        "description": "Look up a single existing booking by its id.",
        "path": "/bookings/{booking_id}",
        "path_params": {
            "booking_id": {
                "type": "string",
                "description": "The id of the booking to look up.",
            },
        },
    },
    {
        "name": "get_customer_bookings",
        "description": "List existing bookings for a customer by name.",
        "path": "/bookings",
        "query_params": {
            "customer_name": {
                "type": "string",
                "description": "The customer's name to search bookings for.",
            },
        },
    },
]

SYSTEM_PROMPT = (
    "You are a booking assistant for a salon. Use search_services to find a "
    "service_id matching what the customer wants. Use search_employees if the "
    "customer asks for a specific staff member. Use search_available_slots to "
    "find open appointment times before suggesting one. Use get_booking or "
    "get_customer_bookings to answer questions about existing bookings. Do not "
    "invent services, employees, or slots that were not returned by a tool."
)


def build_tool_configs(base_url: str) -> list[dict]:
    configs = []
    for tool in TOOL_DEFINITIONS:
        api_schema = {
            "url": f"{base_url}{tool['path']}",
            "method": "GET",
        }
        if "path_params" in tool:
            api_schema["path_params_schema"] = tool["path_params"]
        if "query_params" in tool:
            api_schema["query_params_schema"] = tool["query_params"]

        configs.append(
            {
                "type": "webhook",
                "name": tool["name"],
                "description": tool["description"],
                "api_schema": api_schema,
            }
        )
    return configs


def main() -> None:
    load_dotenv()
    api_key = os.environ["ELEVENLABS_API_KEY"]
    base_url = os.environ.get("API_BASE_URL", DEFAULT_BASE_URL)

    client = ElevenLabs(api_key=api_key)

    tool_ids = []
    for config in build_tool_configs(base_url):
        tool = client.conversational_ai.tools.create(tool_config=config)
        tool_ids.append(tool.id)

    agent = client.conversational_ai.agents.create(
        conversation_config={
            "agent": {
                "prompt": {
                    "prompt": SYSTEM_PROMPT,
                    "tool_ids": tool_ids,
                }
            }
        }
    )
    print(f"Created agent: {agent.agent_id}")


if __name__ == "__main__":
    main()
```

Note: this script is **not executed** in this task — there is no `ELEVENLABS_API_KEY` available. `main()` is exercised manually later by the user once they have ElevenLabs credentials (VBOOK-08 prerequisite). Only `build_tool_configs`, the pure part, is unit tested here.

- [x] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_create_elevenlabs_agent.py -v`
Expected: PASS (4 tests)

- [x] **Step 6: Run the full suite to check for regressions**

Run: `uv run pytest -q`
Expected: all tests pass (39 existing + 4 new = 43)

- [x] **Step 7: Commit**

```bash
git add scripts/__init__.py scripts/create_elevenlabs_agent.py tests/test_create_elevenlabs_agent.py
git commit -m "Add ElevenLabs agent-creation script with webhook tool configs"
```

**Deviation 1 (post-hoc, by user request):** after this task was implemented and committed exactly as planned above (verified 4/4 new tests passing, 43/43 full suite), the user asked to drop the test file from the repo — `scripts/create_elevenlabs_agent.py` is a one-off setup script, not maintained long-term code, so it doesn't warrant committed regression tests. `tests/test_create_elevenlabs_agent.py` was removed in a follow-up commit after being used to verify `build_tool_configs` manually. The script itself (`scripts/create_elevenlabs_agent.py`, `scripts/__init__.py`) remains unchanged at this point. Full suite after removal: 39 passed.

**Deviation 2 (bugs found in code-quality review, fixed post-commit):** with the test file gone, a code-quality reviewer gave the script extra scrutiny by validating its ElevenLabs SDK call shapes against the actually-installed `elevenlabs==2.64.0` package's pydantic models (no API key or network access needed for this — just local model validation). Two bugs were found and are NOT reflected in the `main()`/`build_tool_configs()` code shown in Step 4 above:

1. `client.conversational_ai.tools.create(tool_config=config)` used a keyword argument that doesn't exist on the installed SDK — `ToolsClient.create` requires `request: ToolRequestModel`. Fixed to `client.conversational_ai.tools.create(request={"tool_config": config})`.
2. `query_params_schema` was built as a flat `{param: {type, description}}` dict, but the SDK's `QueryParamsJsonSchema` model requires `{"properties": {...}, "required": [...]}`. Fixed by wrapping the params dict accordingly in `build_tool_configs()`, and adding a `required_query_params` list per tool in `TOOL_DEFINITIONS` (derived from which FastAPI query params have no default: `["service_id", "date"]` for `search_available_slots`, `[]` for the other three query-param tools). `path_params_schema` for `get_booking` was already correct as a flat dict and was left unchanged.

Both fixes were verified by constructing `ToolRequestModel(tool_config=config)` for all 5 `build_tool_configs()` outputs against the installed SDK and confirming they validate without error — still without any real API key or network call. `uv run pytest -q` continued to pass at 39 (unchanged, since this script has no committed tests).

---

### Task 10: Update VBOOK-09 backlog status

**Files:**
- Modify: `docs/BACKLOG.md`
- Move: `docs/backlog/VBOOK-09-connect-elevenlabs-tools-to-fastapi.md` → `docs/done/VBOOK-09-connect-elevenlabs-tools-to-fastapi.md`

- [ ] **Step 1: Move the story file**

```bash
git mv docs/backlog/VBOOK-09-connect-elevenlabs-tools-to-fastapi.md docs/done/VBOOK-09-connect-elevenlabs-tools-to-fastapi.md
```

- [ ] **Step 2: Update the link in `docs/BACKLOG.md`**

Change:

```text
| [VBOOK-09](backlog/VBOOK-09-connect-elevenlabs-tools-to-fastapi.md) | P0 | Connect ElevenLabs tools to FastAPI |
```

to:

```text
| [VBOOK-09](done/VBOOK-09-connect-elevenlabs-tools-to-fastapi.md) | P0 | Connect ElevenLabs tools to FastAPI |
```

- [ ] **Step 3: Run the full suite one last time**

Run: `uv run pytest -q`
Expected: all 43 tests pass

- [ ] **Step 4: Commit**

```bash
git add docs/BACKLOG.md docs/backlog docs/done
git commit -m "Mark VBOOK-09 as done"
```

---

## Manual follow-up (not part of this plan)

Per the design's "out of scope" section, once you have ElevenLabs credentials:

1. Run the app locally: `uv run uvicorn app.main:app --reload`
2. Create a `.env` (from `.env.example`) with your real `ELEVENLABS_API_KEY` and, if not running on `localhost:8000`, an `API_BASE_URL` reachable by ElevenLabs (e.g. via a tunnel).
3. Run `uv run python -m scripts.create_elevenlabs_agent` to create the agent and register the five tools.
4. Talk to the agent and confirm the acceptance criteria: "Find me a haircut tomorrow after six" triggers `search_services` → `search_available_slots` calls against your running FastAPI backend.
5. Iterate on `TOOL_DEFINITIONS` descriptions in `scripts/create_elevenlabs_agent.py` and re-run the script to see how wording changes affect the agent's tool-calling behavior (the VBOOK-09 TODO item this plan doesn't fully resolve).
