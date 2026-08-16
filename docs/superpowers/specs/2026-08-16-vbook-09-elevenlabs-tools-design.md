# VBOOK-09 — Connect ElevenLabs tools to FastAPI — Design

**Story:** [VBOOK-09](../../done/VBOOK-09-connect-elevenlabs-tools-to-fastapi.md)
**Architecture decision:** [ADR 0001](../../adr/0001-elevenlabs-tool-layer-architecture.md)

## Context

VBOOK-09 asks for five read-only tools (`search_services`, `search_employees`,
`search_available_slots`, `get_booking`, `get_customer_bookings`) that an ElevenLabs
conversational agent can call over HTTP. The domain model these tools need — services,
employees, availability — doesn't exist yet: VBOOK-04 (PostgreSQL), VBOOK-05 (availability
search), and VBOOK-06 (transactional booking) are still unimplemented. VBOOK-08 (creating
the ElevenLabs agent itself) is also unimplemented — no SDK dependency or agent script
exists.

Per [ADR 0001](../../adr/0001-elevenlabs-tool-layer-architecture.md), this design adds
minimal in-memory stand-ins scoped to what these tools need (not full VBOOK-04/05/06),
and includes writing (but not executing) an agent-creation script, since no ElevenLabs
API key is available in this environment.

## Data model & seed data

New in-memory repositories, following the existing `InMemory*Repository` +
`get_*_repository` dependency pattern (see `app/repositories/businesses.py`):

- **`app/repositories/services.py`** — `Service`: `id`, `name`, `duration_minutes`, `price`.
  Seeded with a fixed small set (e.g. Haircut, Shave, Manicure) since there's no create
  endpoint for services yet.
- **`app/repositories/employees.py`** — `Employee`: `id`, `name`, `service_ids` (list of
  service ids they perform). Seeded with a couple of employees covering different services.

**Booking** (`app/repositories/bookings.py`, existing) gains one optional field:
`employee_id: str | None = None`, on both the stored booking dict and
`CreateBookingRequest`. Existing bookings/tests that don't set it are unaffected — they
simply don't block any employee's availability.

## Availability logic

**`app/slots.py`** (new, pure function, no I/O, no FastAPI/router dependency):

```python
def generate_available_slots(
    service: dict,
    employees: list[dict],
    bookings: list[dict],
    date: str,               # "YYYY-MM-DD"
    earliest_time: str | None = None,   # "HH:MM"
    latest_time: str | None = None,     # "HH:MM"
    employee_id: str | None = None,
) -> list[dict]:  # [{"employee_id", "employee_name", "start", "end"}, ...]
```

- Every employee works fixed hours: **09:00–17:00**, every day (module-level constant).
- Candidate slots are generated every **30 minutes**; a slot is valid only if
  `start + service["duration_minutes"] <= 17:00`.
- Only employees whose `service_ids` include the requested service are considered
  (further restricted to `employee_id` if given).
- A slot is excluded if a `confirmed` booking exists for that employee with a matching
  `slot` start time.
- `earliest_time`/`latest_time`, if given, filter the generated slots by start time.

## Endpoints

Plain RESTful resources — no `/tools/*` namespace. The ElevenLabs tool *name* is mapped
to a REST URL only inside the agent-creation script, not in the FastAPI routing.

| ElevenLabs tool | Endpoint |
|---|---|
| `search_services` | `GET /services?name=` (new `app/routers/services.py`) |
| `search_employees` | `GET /employees?service_id=` (new `app/routers/employees.py`) |
| `search_available_slots` | `GET /availability?service_id=&date=&earliest_time=&latest_time=&employee_id=` (new `app/routers/availability.py`) |
| `get_booking` | `GET /bookings/{booking_id}` (new handler in existing `app/routers/bookings.py`) |
| `get_customer_bookings` | `GET /bookings?customer_name=` (extends existing `GET /bookings` handler with an optional filter) |

`name` and `customer_name` filters are case-insensitive substring matches (consistent with
a voice agent passing along loosely-transcribed phrases, e.g. "haircut" should match a
service named "Men's Haircut"). `service_id`/`employee_id`/`booking_id` are exact matches.
`date` must be `YYYY-MM-DD`; `earliest_time`/`latest_time` must be `HH:MM` — anything else
is a `400`, per the error-handling section below.

All responses use the existing plain-dict style (`dict[str, list[dict]]` / `dict[str, str]`),
matching `businesses.py`/`bookings.py` today — no new response-model abstraction.

## Logging

Each new/extended handler logs the incoming query params and the outcome via the
standard `logging` module at INFO level (no structured/JSON logging infra — none exists
in the app today). If duplicating the log calls across 5 handlers feels repetitive during
implementation, factor a single small helper — but write it inline first and only extract
if it's clearly repeated verbatim.

## Error handling

- **Malformed arguments:** type mismatches are caught by FastAPI/Pydantic (`422`
  automatically). Domain-level bad input (e.g. unparsable date) → `400` with
  `{"detail": "..."}`.
- **Not found:** unknown `booking_id` → `404` with `{"detail": "..."}`. This requires
  catching the `KeyError` raised by `InMemoryBookingRepository._get` in the new
  `GET /bookings/{id}` handler specifically — the existing cancel/reschedule handlers,
  which have the same latent 500-on-KeyError issue, are left untouched (out of scope for
  this ticket).
- **Empty results:** not an error. `search_services`, `search_employees`,
  `search_available_slots`, and `get_customer_bookings` all return `200` with an empty
  list when nothing matches.

## Agent-creation script

**`scripts/create_elevenlabs_agent.py`** (new):

- Adds `elevenlabs` and `python-dotenv` dependencies. Reads `ELEVENLABS_API_KEY`
  (required) and `API_BASE_URL` (default `http://localhost:8000`) from the environment,
  loaded via `python-dotenv` from a gitignored `.env` (a `.env.example` documents the two
  variables).
- `build_tool_configs(base_url: str) -> list[dict]` — pure function building the 5
  webhook tool configs (`name`, `description`, `api_schema.url`, `.method`,
  `.query_params_schema`), one per row in the endpoint table above. Kept separate from
  network calls so it's unit-testable without an API key.
- `main()` calls `elevenlabs.conversational_ai.tools.create(...)` for each config, then
  creates an agent with a system prompt describing when to use each tool, attaching the
  resulting tool ids. Prints the created agent id.
- **Not executed in this session** — no ElevenLabs API key is available yet. The user
  runs this manually once they've created an account/key (VBOOK-08 prerequisite).
- Tool description wording ("Experiment with tool descriptions to see how they affect
  agent behavior" from the VBOOK-09 TODO) is a manual, iterative learning activity done
  by editing this script and re-running it against the live agent — not something to
  fully resolve in this implementation pass.

## Testing

pytest + `TestClient`, matching the existing style in `tests/`:

- `tests/test_services.py` — search/filter by name, empty results.
- `tests/test_employees.py` — search/filter by service_id, empty results.
- `tests/test_slots.py` — unit tests for `generate_available_slots`: working-hours
  boundaries, excluding already-booked slots, `earliest_time`/`latest_time` filtering,
  unknown service/employee.
- `tests/test_bookings.py` — extended with `GET /bookings/{id}` (found and 404 cases) and
  `GET /bookings?customer_name=` (match, case-insensitive match, no match).
- `tests/test_create_elevenlabs_agent.py` — unit test for `build_tool_configs()` shape
  only; no real network/API calls.

## Out of scope

- Real persistence (PostgreSQL/SQLAlchemy) — VBOOK-04.
- Real overlap/concurrency-safe booking creation — VBOOK-06.
- Per-employee working hours, business-scoped services/employees, create endpoints for
  services/employees.
- Fixing the pre-existing 500-on-unknown-id bug in `POST /bookings/{id}/cancel` and
  `.../reschedule`.
- Executing the agent-creation script against the real ElevenLabs API.
