# VBOOK-10 — Implement voice booking with explicit confirmation

**Priority:** P0
**Goal:** Safely allow an LLM-driven interface to mutate transactional state.

## Description

Allow the agent to create a booking.

A booking must **never** happen until the user explicitly confirms the final details.

## Expected flow

```text
USER:
Book me tomorrow after six.

AGENT:
Adam has 18:00 and Julia has 18:30.

USER:
Take Adam.

AGENT:
That's a men's haircut with Adam tomorrow
at 18:00 for 100 PLN. Should I book it?

USER:
Yes.

          ↓

create_booking(...)
```

## TODO

* [x] Add `create_booking` ElevenLabs tool
* [x] Define required arguments
* [x] Require explicit user confirmation (backend-enforced `confirmed: bool`, reinforced
      by the system prompt)
* [x] Prevent accidental execution during slot exploration (same `confirmed` gate, plus
      explicit tool-description wording not to call it speculatively)
* [ ] Pass an idempotency key — `POST /bookings` supports `Idempotency-Key`, but the
      ElevenLabs `create_booking` tool config doesn't set the header, so voice-driven
      calls don't get idempotency protection yet
* [ ] Handle slot becoming unavailable after confirmation — deferred to
      [VBOOK-15](VBOOK-15-add-booking-holds-for-safer-voice-confirmation.md)'s hold/confirm design
* [ ] Have the agent offer alternatives
* [ ] Handle ambiguous responses such as:

  * “sure”
  * “okay”
  * “maybe”
  * “actually no”

  (currently only addressed via system-prompt wording, not deterministically)
* [ ] Add conversation-level tests
* [ ] Store tool execution audit records (currently just `logger.info` request/response
      lines, not durable records)

## Learning objectives

Explore the boundary between:

* probabilistic LLM behavior
* deterministic backend rules

## Acceptance criteria

A complete booking can be performed **using voice only** with no clicks or visual UI.
