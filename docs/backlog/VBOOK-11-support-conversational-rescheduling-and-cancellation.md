# VBOOK-11 — Support conversational rescheduling and cancellation

**Priority:** P1
**Goal:** Exercise conversational state and references.

## Description

Support voice commands referring to existing context.

Examples:

> Cancel my appointment tomorrow.

> Move it to Friday.

> Anything around the same time?

> Take the earlier one.

## TODO

* [ ] Add `cancel_booking`
* [ ] Add `reschedule_booking`
* [ ] Implement `get_customer_bookings`
* [ ] Require confirmation before mutations
* [ ] Resolve phrases such as:

  * “my next appointment”
  * “it”
  * “the Friday one”
  * “same barber”
  * “same time”
  * “earlier one”
* [ ] Handle multiple matching bookings
* [ ] Ask for clarification only when necessary
* [ ] Preserve transaction safety
* [ ] Add integration tests

## Learning objectives

Explore how conversational context interacts with deterministic IDs and domain state.

## Acceptance criteria

The following conversation succeeds without UI:

```text
"When is my next haircut?"

"Tomorrow at 18:00."

"Move it to Friday around the same time."

"17:30 and 18:30 are available."

"Earlier one."

"Move it to Friday at 17:30?"

"Yes."
```
