# Voice-First Booking — JIRA Backlog

Each story lives in its own file under [`docs/backlog/`](backlog/).

| Story | Priority | Title |
| --- | --- | --- |
| [VBOOK-01](backlog/VBOOK-01-bootstrap-the-python-project.md) | P0 | Bootstrap the Python project |
| [VBOOK-02](backlog/VBOOK-02-learn-fastapi-and-build-the-api-skeleton.md) | P0 | Learn FastAPI and build the API skeleton |
| [VBOOK-03](backlog/VBOOK-03-model-the-booking-domain-in-python.md) | P0 | Model the booking domain in Python |
| [VBOOK-04](backlog/VBOOK-04-add-postgresql-and-async-sqlalchemy.md) | P0 | Add PostgreSQL and async SQLAlchemy |
| [VBOOK-05](backlog/VBOOK-05-implement-appointment-availability-search.md) | P0 | Implement appointment availability search |
| [VBOOK-06](backlog/VBOOK-06-implement-transactional-booking.md) | P0 | Implement transactional booking |
| [VBOOK-07](backlog/VBOOK-07-add-idempotency-and-safe-mutations.md) | P0 | Add idempotency and safe mutations |
| [VBOOK-08](backlog/VBOOK-08-build-the-first-elevenlabs-conversational-agent.md) | P0 | Build the first ElevenLabs conversational agent |
| [VBOOK-09](backlog/VBOOK-09-connect-elevenlabs-tools-to-fastapi.md) | P0 | Connect ElevenLabs tools to FastAPI |
| [VBOOK-10](backlog/VBOOK-10-implement-voice-booking-with-explicit-confirmation.md) | P0 | Implement voice booking with explicit confirmation |
| [VBOOK-11](backlog/VBOOK-11-support-conversational-rescheduling-and-cancellation.md) | P1 | Support conversational rescheduling and cancellation |
| [VBOOK-12](backlog/VBOOK-12-learn-asyncio-through-parallel-availability-search.md) | P1 | Learn asyncio through parallel availability search |
| [VBOOK-13](backlog/VBOOK-13-create-a-proper-automated-test-suite.md) | P1 | Create a proper automated test suite |
| [VBOOK-14](backlog/VBOOK-14-add-conversation-observability-and-evaluation.md) | P1 | Add conversation observability and evaluation |

## Recommended implementation order

```text
PHASE 1 — Learn Python backend
VBOOK-01
    ↓
VBOOK-02
    ↓
VBOOK-03
    ↓
VBOOK-04
    ↓
VBOOK-05
    ↓
VBOOK-06
    ↓
VBOOK-07

PHASE 2 — Learn ElevenLabs
VBOOK-08
    ↓
VBOOK-09
    ↓
VBOOK-10

        ★ FIRST REAL MVP ★

PHASE 3 — Go deeper
VBOOK-11
VBOOK-12
VBOOK-13
VBOOK-14
```

## MVP definition

Do **not** wait for all tickets.

The first meaningful milestone is complete after **VBOOK-10**.

At that point you should be able to call the agent and say:

> “I'd like a haircut tomorrow after 6 PM.”

and complete the entire search → selection → confirmation → booking process using your voice.

That is the first version worth showing to someone.
