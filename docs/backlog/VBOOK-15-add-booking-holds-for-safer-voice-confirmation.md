# VBOOK-15 — Add booking holds for safer voice confirmation

**Priority:** P1
**Goal:** Replace prompt-only confirmation with a structural safeguard against premature bookings.

## Description

VBOOK-10 exposed `create_booking` to the agent with a required `confirmed: true`
argument, enforced by the backend. That's a real improvement over no gate at all, but
it's still just the LLM asserting a flag — there's no platform-level guarantee from
ElevenLabs that a tool call only happens after real user confirmation (confirmed
directly with ElevenLabs: there is no "requires approval" mechanism for webhook tools;
it's prompt engineering all the way down).

This story replaces the single `create_booking` call with a two-step flow that makes
premature booking structurally harder, not just discouraged by wording:

```text
search_available_slots (existing, unchanged)
        │
        ▼
hold_booking(service_id, employee_id, slot, customer_name)
   - validates the slot is currently available (reuses generate_available_slots)
   - creates a short-lived pending hold (e.g. 5 minute TTL)
   - returns hold_id + a human-readable summary (service, employee, time, price)
        │   agent reads the summary back, asks "Should I book it?"
        ▼
confirm_booking(hold_id)
   - re-validates the slot is still available (something else may have taken it
     during the hold window)
   - creates the real booking
   - idempotent: confirming an already-confirmed hold returns the same booking
     instead of creating a duplicate
```

## TODO

* [ ] Add `InMemoryBookingHoldRepository` (mirror `app/idempotency.py`'s TTL/clock
      pattern for lazy expiry rather than active sweeping)
* [ ] Add `POST /booking-holds` (`hold_booking` tool): validate service/employee/slot,
      reject with 404/400/409 as appropriate, return hold summary
* [ ] Add `POST /booking-holds/{hold_id}/confirm` (`confirm_booking` tool): 404 if
      unknown, 410 if expired, 409 if slot no longer available, idempotent replay if
      already confirmed
* [ ] Retire the single-step `create_booking` tool from the agent config (decide
      whether to keep the underlying `POST /bookings` endpoint for direct/non-voice
      use, since other callers may still want one-shot creation)
* [ ] Update `scripts/create_elevenlabs_agent.py`: swap tool registration, rewrite the
      system prompt around the two-step flow, mirroring VBOOK-10's example dialogue
* [ ] Tests: hold rejected when slot unavailable, confirm rejected when hold expired,
      confirm rejected when slot taken since hold was created, confirm is idempotent,
      confirm of unknown hold_id returns 404
* [ ] Decide and document the hold TTL
* [ ] (Optional, discuss before building) explicit `cancel_booking_hold` tool for
      "actually no" responses, vs. just letting holds expire naturally

## Explicitly out of scope

* Real concurrency-safe locking (VBOOK-06) — re-validation here is best-effort, not
  race-proof; two confirms racing on the same slot in the same instant could still
  both pass validation before either writes. That's VBOOK-06's problem to solve
  properly once persistence exists.
* Conversation-level behavior work already listed on VBOOK-10 (offering alternatives,
  handling ambiguous responses like "maybe", audit records) — this story is about the
  backend contract, not agent conversational tuning.

## Learning objectives

Explore how to move a safety property from "the LLM should behave" to "the system
structurally can't proceed without two separate, validated steps" — and where that
structural guarantee still has gaps (the re-validation race above) versus where real
transactional guarantees (VBOOK-06) are required.

## Acceptance criteria

A booking can only be created after two separate, explicitly-confirmed tool calls; a
slot that becomes unavailable between hold and confirm is rejected with a clear error
rather than silently double-booked.
