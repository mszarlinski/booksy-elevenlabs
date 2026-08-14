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

* [ ] Add `create_booking` ElevenLabs tool
* [ ] Define required arguments
* [ ] Require explicit user confirmation
* [ ] Prevent accidental execution during slot exploration
* [ ] Pass an idempotency key
* [ ] Handle slot becoming unavailable after confirmation
* [ ] Have the agent offer alternatives
* [ ] Handle ambiguous responses such as:

  * “sure”
  * “okay”
  * “maybe”
  * “actually no”
* [ ] Add conversation-level tests
* [ ] Store tool execution audit records

## Learning objectives

Explore the boundary between:

* probabilistic LLM behavior
* deterministic backend rules

## Acceptance criteria

A complete booking can be performed **using voice only** with no clicks or visual UI.
