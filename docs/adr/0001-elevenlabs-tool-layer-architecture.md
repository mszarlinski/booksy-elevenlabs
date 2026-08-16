# ADR 0001 — Architecture for connecting ElevenLabs tools to FastAPI

**Status:** Accepted
**Date:** 2026-08-15
**Related:** VBOOK-09

## Context

VBOOK-09 requires exposing five read-only tools (`search_services`, `search_employees`,
`search_available_slots`, `get_booking`, `get_customer_bookings`) that an ElevenLabs
conversational agent can call over HTTP.

The domain model these tools depend on (services, employees, availability) does not exist
yet — VBOOK-04 (PostgreSQL), VBOOK-05 (availability search), and VBOOK-06 (transactional
booking) are still unimplemented. Rather than pulling those stories forward in full, we're
adding minimal in-memory stand-ins scoped tightly to what the tools need, so this ticket
stays focused on learning ElevenLabs tool-calling rather than re-doing later stories early.

VBOOK-08 (creating an ElevenLabs agent) is also unimplemented — no ElevenLabs SDK dependency
or agent script exists yet.

## Decision

Split the work into two independently runnable pieces:

```text
ElevenLabs Agent (created by scripts/create_elevenlabs_agent.py)
      │  webhook tool calls (HTTP)
      ▼
GET /services            (app/routers/services.py)      ← search_services
GET /employees           (app/routers/employees.py)     ← search_employees
GET /availability        (app/routers/availability.py)  ← search_available_slots
GET /bookings/{id}       (app/routers/bookings.py)       ← get_booking
GET /bookings?customer_name=  (app/routers/bookings.py)  ← get_customer_bookings
      │
      ├─ app/repositories/services.py   (new, seeded in-memory)
      ├─ app/repositories/employees.py  (new, seeded in-memory)
      ├─ app/repositories/bookings.py   (existing, gains employee_id)
      └─ app/slots.py                   (new, pure slot-generation logic)
```

Endpoints are plain RESTful resources (`/services`, `/employees`, `/availability`,
`/bookings/{id}`) rather than a `/tools/*` namespace mirroring the ElevenLabs tool names.
The mapping from ElevenLabs tool identifier (e.g. `search_services`) to REST URL happens
only in the agent-creation script's webhook tool config — the FastAPI app has no notion
of "tools" in its routing.

1. **FastAPI side is self-contained and testable without ElevenLabs credentials.**
   New `services` and `employees` repositories follow the existing
   `InMemory*Repository` + `get_*_repository` dependency pattern already used by
   `businesses` and `bookings`. Seed data is hardcoded since there are no create
   endpoints for services/employees yet (out of scope for this ticket).

2. **Availability logic is a pure, separately testable module** (`app/slots.py`),
   not embedded in the router, mirroring how `app/idempotency.py` already sits outside
   both `routers/` and `repositories/` as cross-cutting domain logic.

3. **Agent creation/configuration is a standalone script**, not part of the app runtime.
   It reads `ELEVENLABS_API_KEY` and `API_BASE_URL` from the environment, builds the five
   webhook tool configs, and registers them on an agent. It is written and reviewed as
   part of this ticket but not executed against the real API in this session (no API key
   available yet) — the user runs it later once they have ElevenLabs credentials.

## Consequences

- The tool endpoints, seed data, and slot logic will need to be revisited/replaced when
  VBOOK-04/05/06 land (real persistence, real overlap/concurrency handling). This is
  expected and acceptable — it's flagged here so it isn't mistaken for the final design.
- Booking gains an optional `employee_id` field so `search_available_slots` can exclude
  slots already booked for a given employee. Bookings without it don't block anyone's
  availability, so this is backward compatible with existing data/tests.
- Because the agent script isn't executed here, the ticket's acceptance criteria (saying
  a phrase to the agent and having it query the real backend) can only be manually
  verified once the user runs the script with real credentials.
