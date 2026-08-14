# VBOOK-14 — Add conversation observability and evaluation

**Priority:** P1
**Goal:** Learn how to operate an LLM/voice product rather than merely demo it.

## Description

Capture enough information to understand why conversations succeed or fail.

## TODO

* [ ] Generate a `conversation_id`
* [ ] Correlate:

  * ElevenLabs conversation
  * HTTP requests
  * tool calls
  * bookings
* [ ] Add structured Python logging
* [ ] Log latency per tool
* [ ] Record:

  * conversation started
  * tool called
  * tool failed
  * booking created
  * booking cancelled
* [ ] Store anonymized transcripts if appropriate
* [ ] Define success metrics
* [ ] Measure:

  * booking completion rate
  * average number of turns
  * tool error rate
  * booking conflicts
  * latency
* [ ] Create 20 synthetic user scenarios
* [ ] Run them against the agent
* [ ] Identify recurring failures
* [ ] Tune agent instructions based on results

## Learning objectives

Understand that LLM systems require evaluation and observability in addition to ordinary application monitoring.

## Acceptance criteria

For any failed conversation you can reconstruct:

```text
what the user asked
→ what the agent understood
→ which tools it called
→ what the backend returned
→ why the booking failed
```
